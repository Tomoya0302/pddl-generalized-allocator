# tests/test_pddl_parser.py

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# --- プロジェクトルートを sys.path に追加 -----------------------------------------
# このファイル: <project_root>/tests/test_pddl_parser.py
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
from pddl_generalized_allocator.utils.log import get_logger


logger = get_logger("test_pddl_parser")


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Test PDDL parser (DomainLoader / ProblemLoader) "
                    "on CoDMAP/MA-PDDL files."
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

    args = parser.parse_args(argv)

    logger.info("=== Parsing domain ===")
    domain_ast = parse_domain(args.domain)

    logger.info("=== Parsing problem ===")
    problem_ast = parse_problem(args.problem)

    # ドメイン名の整合性チェック
    if domain_ast.name != problem_ast.domain_name:
        logger.warning(
            f"Domain name mismatch: domain={domain_ast.name!r}, "
            f"problem.domain={problem_ast.domain_name!r}"
        )
        # CoDMAP では一致していることを期待するので assert してもよい
        assert False, "Domain name in problem does not match domain file"

    logger.info("All basic checks passed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
