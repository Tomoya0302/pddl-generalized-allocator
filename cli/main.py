from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

from pddl_generalized_allocator.utils.log import get_logger
from pddl_generalized_allocator.utils.errors import CodmapPlannerError

from pddl_generalized_allocator.pddl.lexer import Lexer
from pddl_generalized_allocator.pddl.sexp_parser import SExpParser
from pddl_generalized_allocator.pddl.domain_loader import DomainLoader
from pddl_generalized_allocator.pddl.problem_loader import ProblemLoader

from pddl_generalized_allocator.model.types import build_planning_task, GroundAtom
# from pddl_generalized_allocator.model.ma_types import Agent, MultiAgentTask
# from pddl_generalized_allocator.analysis.capabilities import build_capabilities
from pddl_generalized_allocator.model.ma_types import MultiAgentTask
from pddl_generalized_allocator.analysis.capabilities import build_agents_and_capabilities_auto
from pddl_generalized_allocator.decomposition.multi_solution import (
    generate_multiple_solutions,
    DecompositionAllocationSolution,
)


logger = get_logger("pddl_generalized_allocator.cli")


# ---------------------------------------------------------------------------
# ヘルパ: PDDL ファイル読み込み & パース
# ---------------------------------------------------------------------------


def _parse_domain(domain_path: str):
    with open(domain_path, "r", encoding="utf-8") as f:
        text = f.read()

    tokens = Lexer(text).tokenize()
    sexps = SExpParser(tokens).parse()
    domain_ast = DomainLoader(sexps).load()

    logger.info(
        "Parsed domain: name=%s, #predicates=%d, #actions=%d",
        domain_ast.name,
        len(domain_ast.predicates),
        len(domain_ast.actions),
    )
    return domain_ast


def _parse_problem(problem_path: str):
    with open(problem_path, "r", encoding="utf-8") as f:
        text = f.read()

    tokens = Lexer(text).tokenize()
    sexps = SExpParser(tokens).parse()
    problem_ast = ProblemLoader(sexps).load()

    logger.info(
        "Parsed problem: name=%s, domain=%s, #objects=%d, #init=%d, #agents=%d",
        problem_ast.name,
        problem_ast.domain_name,
        len(problem_ast.objects),
        len(problem_ast.init),
        len(problem_ast.agents),
    )
    return problem_ast


# ---------------------------------------------------------------------------
# ヘルパ: Solution → JSON 変換
# ---------------------------------------------------------------------------


def _atom_to_str(atom: GroundAtom) -> str:
    arg_str = " ".join(o.name for o in atom.args)
    return f"({atom.predicate.name} {arg_str})"


def _serialize_solution(
    sol: DecompositionAllocationSolution,
) -> Dict[str, Any]:
    """
    DecompositionAllocationSolution をシリアライズ可能な dict に変換。

    スキーマ（1 solution あたり）:
      {
        "subtasks": [
          {
            "id": 0,
            "goals": ["(p a b)", ...],
            "involved_predicates": ["p", "q", ...],
            "assigned_agent": "agent1",
            "assignment_cost": 0.5
          },
          ...
        ]
      }
    """
    # subtask.id → {agent_name, cost}
    subtask_assign_info: Dict[int, Dict[str, Any]] = {}
    for assign in sol.allocation.assignments:
        sid = assign.subtask.id
        subtask_assign_info[sid] = {
            "agent": assign.agent.name if assign.agent is not None else None,
            "cost": assign.cost,
        }

    subtasks_payload: List[Dict[str, Any]] = []
    for st in sol.subtasks:
        info = subtask_assign_info.get(st.id, {"agent": None, "cost": None})
        subtasks_payload.append(
            {
                "id": st.id,
                "goals": [_atom_to_str(g) for g in st.goal_atoms],
                "involved_predicates": sorted(list(st.involved_predicates)),
                "assigned_agent": info["agent"],
                "assignment_cost": info["cost"],
            }
        )

    return {"subtasks": subtasks_payload}


def serialize_solutions_to_json(
    domain_name: str,
    problem_name: str,
    solutions: List[DecompositionAllocationSolution],
) -> str:
    """
    全 solution を JSON 文字列としてシリアライズする。

    トップレベルスキーマ:
      {
        "domain": "logistics",
        "problem": "p01",
        "num_solutions": N,
        "solutions": [ ... ]
      }
    """
    payload: Dict[str, Any] = {
        "domain": domain_name,
        "problem": problem_name,
        "num_solutions": len(solutions),
        "solutions": [_serialize_solution(sol) for sol in solutions],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# メインパイプライン
# ---------------------------------------------------------------------------


def run(
    domain_path: str,
    problem_path: str,
    num_solutions: int = 5,
    random_seed: Optional[int] = 42,
    max_subtasks: Optional[int] = None,
) -> str:
    """
    End-to-end:
      domain.pddl + problem.pddl →
      DomainAST, ProblemAST →
      PlanningTask →
      MultiAgentTask →
      複数の分解＋割当案 →
      JSON 文字列
    """
    # 1. PDDL パース
    domain_ast = _parse_domain(domain_path)
    problem_ast = _parse_problem(problem_path)

    if domain_ast.name != problem_ast.domain_name:
        raise CodmapPlannerError(
            f"Domain name mismatch: domain '{domain_ast.name}' "
            f"vs problem ':domain {problem_ast.domain_name}'"
        )

    # 2. PlanningTask 構築
    planning_task = build_planning_task(domain_ast, problem_ast)

    # 3. MultiAgentTask 構築
    agents, capabilities = build_agents_and_capabilities_auto(
        planning_task,
        problem_ast,
    )

    ma_task = MultiAgentTask(
        planning_task=planning_task,
        agents=agents,
        capabilities=capabilities,
    )

    # 4. 解案生成
    solutions = generate_multiple_solutions(
        ma_task,
        num_solutions=num_solutions,
        random_seed=random_seed,
        max_num_subtasks=max_subtasks,
    )

    # 5. JSON 文字列に変換
    json_str = serialize_solutions_to_json(
        domain_name=domain_ast.name,
        problem_name=problem_ast.name,
        solutions=solutions,
    )
    return json_str


# ---------------------------------------------------------------------------
# CLI エントリポイント
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "CoDMAP-15 style MA-PDDL domain/problem から "
            "汎用タスク分解＋割当案を生成して JSON ファイルに出力する CLI"
        )
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Path to domain PDDL file",
    )
    parser.add_argument(
        "--problem",
        required=True,
        help="Path to problem PDDL file",
    )
    parser.add_argument(
        "--num-solutions",
        type=int,
        default=5,
        help="Number of decomposition+allocation solutions to generate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for solution diversity",
    )
    parser.add_argument(
        "--max-subtasks",
        type=int,
        default=None,
        help="Maximum number of subtasks per solution (if omitted, no explicit limit)",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Path to output JSON file",
    )

    args = parser.parse_args(argv)

    try:
        json_str = run(
            domain_path=args.domain,
            problem_path=args.problem,
            num_solutions=args.num_solutions,
            random_seed=args.seed,
            max_subtasks=args.max_subtasks,
        )
        # ファイルに書き込む
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        logger.info("Wrote output JSON to: %s", args.output)
        # 標準出力にはパスだけ軽く出す（必要なければ消してもOK）
        print(f"Output written to {args.output}")
        return 0
    except CodmapPlannerError as e:
        logger.error("CodmapPlannerError: %s", e)
        return 1
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
