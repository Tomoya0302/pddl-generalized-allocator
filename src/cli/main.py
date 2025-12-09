import argparse
import json
from ..config.loader import load_config
from ..pddl.tokenizer import tokenize
from ..pddl.sexpr_parser import parse_sexpr
from ..pddl.domain_parser import DomainParser
from ..pddl.problem_parser import ProblemParser
from ..planning.task import PlanningTask
from ..multiagent.agents import extract_agents, MultiAgentTask
from ..multiagent.capabilities import compute_capabilities
from ..planning.clustering import build_subtasks_with_retry
from ..planning.allocation import allocate_subtasks
from ..utils.random_utils import RandomState

def main():
    parser = argparse.ArgumentParser(description="PDDL Multi-Agent Task Decomposition & Allocation")
    parser.add_argument("--config", default="configs/default_config.yaml", help="Config file path")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    args = parser.parse_args()

    cfg = load_config(args.config)

    # --- PDDL パース ---
    print(f"Loading domain: {cfg.pddl.domain_file}")
    with open(cfg.pddl.domain_file, encoding="utf-8") as f:
        domain_tokens = tokenize(f.read())
    
    print(f"Loading problem: {cfg.pddl.problem_file}")
    with open(cfg.pddl.problem_file, encoding="utf-8") as f:
        problem_tokens = tokenize(f.read())

    domain_sexprs = parse_sexpr(domain_tokens)
    problem_sexprs = parse_sexpr(problem_tokens)

    domain_ast = DomainParser(domain_sexprs).parse()
    problem_ast = ProblemParser(problem_sexprs).parse()

    task = PlanningTask.from_ast(domain_ast, problem_ast)
    
    print(f"Parsed domain '{domain_ast.name}' with {len(domain_ast.actions)} actions")
    print(f"Parsed problem '{problem_ast.name}' with {len(problem_ast.objects)} objects and {len(task.goals)} goals")

    # --- Multi-agent 準備 ---
    agents = extract_agents(task, cfg.multiagent.agent_types)
    capabilities = compute_capabilities(task, agents, cfg.multiagent.agent_types)
    ma_task = MultiAgentTask(planning_task=task, agents=agents)
    
    print(f"Found {len(agents)} agents: {list(agents.keys())}")

    # --- サブタスク構築 ---
    print("Building subtasks with retry...")
    rng = RandomState(seed=cfg.clustering.random_seed)
    subtasks = build_subtasks_with_retry(task,
                                         cfg.clustering,
                                         cfg.roles,
                                         rng)
    
    print(f"Generated {len(subtasks)} subtasks")

    # --- 割当 ---
    print("Allocating subtasks to agents...")
    from ..planning.roles import load_domain_role_config
    role_cfg = load_domain_role_config(cfg.roles.role_config_file)
    assignment = allocate_subtasks(subtasks, capabilities, task, role_cfg, cfg.allocation.cost_function)

    # --- 結果出力 ---
    result = {
        "domain": domain_ast.name,
        "problem": problem_ast.name,
        "subtasks": [],
        "assignment": assignment,
        "agents": {name: {"name": agent.name, "type": agent.type_name} 
                   for name, agent in agents.items()},
        "capabilities": {name: list(caps) for name, caps in capabilities.items()}
    }
    
    for subtask in subtasks:
        subtask_data = {
            "id": subtask.id,
            "goals": [str(goal) for goal in subtask.goals],
            "landmark_predicates": list(subtask.landmark_predicates),
            "role_signature": subtask.role_signature,
            "assigned_agent": assignment.get(subtask.id)
        }
        result["subtasks"].append(subtask_data)
    
    # JSON出力
    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Results saved to {args.output}")
    else:
        print("\n=== RESULTS ===")
        print(output_json)

if __name__ == "__main__":
    main()