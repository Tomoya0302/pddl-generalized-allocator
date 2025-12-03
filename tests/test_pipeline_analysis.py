from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# --- プロジェクトルートを sys.path に追加 -----------------------------------------
# このファイル: <project_root>/tests/test_pipeline_analysis.py
# project_root を sys.path に入れて、pddl_generalized_allocator パッケージを import 可能にする。
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ここから pddl_generalized_allocator を import
from pddl_generalized_allocator.pddl.lexer import Lexer
from pddl_generalized_allocator.pddl.sexp_parser import SExpParser
from pddl_generalized_allocator.pddl.domain_loader import DomainLoader
from pddl_generalized_allocator.pddl.problem_loader import ProblemLoader

from pddl_generalized_allocator.model.types import build_planning_task
from pddl_generalized_allocator.model.ma_types import Agent, MultiAgentTask
from pddl_generalized_allocator.analysis.capabilities import build_capabilities
from pddl_generalized_allocator.decomposition.multi_solution import (
    generate_multiple_solutions,
    DecompositionAllocationSolution,
)

from pddl_generalized_allocator.utils.log import get_logger


logger = get_logger("test_pipeline_analysis")


# ---------------------------------------------------------------------------
# PDDL パーサ部分のヘルパ（test_pddl_parser.py と同様の構造）
# ---------------------------------------------------------------------------


def parse_domain(domain_path: str):
    """
    指定された domain.pddl をパースして DomainAST を返すヘルパ。
    """
    if not os.path.isfile(domain_path):
        raise FileNotFoundError(f"Domain file not found: {domain_path}")

    with open(domain_path, "r", encoding="utf-8") as f:
        domain_text = f.read()

    logger.info(f"Lexing domain: {domain_path}")
    tokens = Lexer(domain_text).tokenize()
    logger.info(f"Domain tokens: {len(tokens)}")

    sexps = SExpParser(tokens).parse()
    logger.info(f"Domain top-level S-expressions: {len(sexps)}")

    domain_ast = DomainLoader(sexps).load()
    logger.info(f"Parsed domain name: {domain_ast.name}")
    logger.info(f"  #requirements: {len(domain_ast.requirements)}")
    logger.info(f"  #types      : {len(domain_ast.types)}")
    logger.info(f"  #predicates : {len(domain_ast.predicates)}")
    logger.info(f"  #actions    : {len(domain_ast.actions)}")

    # 簡単な検査
    assert domain_ast.name, "Domain name must not be empty"
    assert len(domain_ast.predicates) > 0, "Domain must define at least one predicate"
    assert len(domain_ast.actions) > 0, "Domain must define at least one action"

    return domain_ast


def parse_problem(problem_path: str):
    """
    指定された problem.pddl をパースして ProblemAST を返すヘルパ。
    """
    if not os.path.isfile(problem_path):
        raise FileNotFoundError(f"Problem file not found: {problem_path}")

    with open(problem_path, "r", encoding="utf-8") as f:
        problem_text = f.read()

    logger.info(f"Lexing problem: {problem_path}")
    tokens = Lexer(problem_text).tokenize()
    logger.info(f"Problem tokens: {len(tokens)}")

    sexps = SExpParser(tokens).parse()
    logger.info(f"Problem top-level S-expressions: {len(sexps)}")

    problem_ast = ProblemLoader(sexps).load()
    logger.info(f"Parsed problem name: {problem_ast.name}")
    logger.info(f"  domain name : {problem_ast.domain_name}")
    logger.info(f"  #objects    : {len(problem_ast.objects)}")
    logger.info(f"  #init facts : {len(problem_ast.init)}")
    logger.info(f"  goal is None? {problem_ast.goal is None}")
    logger.info(f"  #agents     : {len(problem_ast.agents)}")

    # 簡単な検査
    assert problem_ast.name, "Problem name must not be empty"
    assert problem_ast.domain_name, "Problem must specify :domain"
    assert len(problem_ast.init) > 0, ":init must contain at least one atom"
    assert problem_ast.goal is not None, ":goal must not be None"

    # MA-PDDL 前提の CoDMAP では agents がいるはず
    assert len(problem_ast.agents) > 0, "No agents found (check :agents or objects of type 'agent')"

    return problem_ast


# ---------------------------------------------------------------------------
# パイプライン全体のテスト
# ---------------------------------------------------------------------------


def run_pipeline(domain_path: str, problem_path: str, num_solutions: int = 3) -> int:
    """
    DomainLoader → ProblemLoader → build_planning_task → MultiAgentTask →
    generate_multiple_solutions までを通すパイプラインテスト。
    """
    logger.info("=== Parsing domain ===")
    domain_ast = parse_domain(domain_path)

    logger.info("=== Parsing problem ===")
    problem_ast = parse_problem(problem_path)

    # ドメイン名の整合性チェック
    assert (
        domain_ast.name == problem_ast.domain_name
    ), f"Domain name mismatch: domain={domain_ast.name!r}, problem.domain={problem_ast.domain_name!r}"

    # --- PlanningTask 構築 ---
    logger.info("=== Building PlanningTask ===")
    planning_task = build_planning_task(domain_ast, problem_ast)
    logger.info(f"PlanningTask.domain_name = {planning_task.domain_name}")
    logger.info(f"#objects   = {len(planning_task.objects)}")
    logger.info(f"#predicates= {len(planning_task.predicates)}")
    logger.info(f"#actions   = {len(planning_task.actions)}")
    logger.info(f"#init      = {len(planning_task.init)}")
    logger.info(f"goal is None? {planning_task.goal is None}")

    assert planning_task.domain_name == domain_ast.name
    assert len(planning_task.objects) > 0
    assert len(planning_task.predicates) > 0
    assert len(planning_task.actions) > 0
    assert len(planning_task.init) > 0

    # --- MultiAgentTask 構築 ---
    logger.info("=== Building MultiAgentTask ===")
    agents = [Agent(name) for name in problem_ast.agents]
    logger.info(f"#agents = {len(agents)}")
    assert len(agents) > 0

    capabilities = build_capabilities(planning_task, agents)
    logger.info("Capabilities:")
    for a in agents:
        caps = capabilities.get(a.name)
        if caps is None:
            logger.warning(f"  Agent {a.name}: no capabilities")
        else:
            logger.info(f"  Agent {a.name}: {len(caps.actions)} actions")

    ma_task = MultiAgentTask(
        planning_task=planning_task,
        agents=agents,
        capabilities=capabilities,
    )

    # --- 分解＋割当案生成 ---
    logger.info("=== Generating decomposition & allocation solutions ===")
    solutions: list[DecompositionAllocationSolution] = generate_multiple_solutions(
        ma_task, num_solutions=num_solutions, random_seed=42
    )

    logger.info(f"#solutions = {len(solutions)}")
    assert len(solutions) == num_solutions

    for idx, sol in enumerate(solutions):
        logger.info(f"--- Solution {idx} ---")
        logger.info(f"  #subtasks    = {len(sol.subtasks)}")
        logger.info(f"  #assignments = {len(sol.allocation.assignments)}")

        # サブタスクと割当の簡単な整合性チェック
        assert len(sol.subtasks) > 0, "No subtasks generated"

        # 各 Assignment が妥当かチェック
        for assign in sol.allocation.assignments:
            assert assign.subtask in sol.subtasks, "Assignment refers to unknown SubTask"
            assert assign.agent in ma_task.agents, "Assignment refers to unknown Agent"
            # cost は有限値であるべき
            assert assign.cost >= 0.0

    logger.info("Pipeline analysis test passed successfully.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Test full pipeline: DomainLoader→ProblemLoader→"
            "PlanningTask→MultiAgentTask→generate_multiple_solutions"
        )
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Path to domain PDDL file "
        "(e.g., universal-pddl-parser-multiagent/domains/codmap15/logistics/domain.pddl)",
    )
    parser.add_argument(
        "--problem",
        required=True,
        help="Path to problem PDDL file "
        "(e.g., universal-pddl-parser-multiagent/domains/codmap15/logistics/p01.pddl)",
    )
    parser.add_argument(
        "--num-solutions",
        type=int,
        default=3,
        help="Number of decomposition+allocation solutions to generate",
    )

    args = parser.parse_args(argv)

    return run_pipeline(args.domain, args.problem, num_solutions=args.num_solutions)


if __name__ == "__main__":
    raise SystemExit(main())
