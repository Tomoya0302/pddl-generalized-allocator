from __future__ import annotations

from typing import Dict, List, Optional
from collections import defaultdict

from pddl_generalized_allocator.pddl.ast import ProblemAST
from pddl_generalized_allocator.model.types import PlanningTask, Object, ActionSchema
from pddl_generalized_allocator.model.ma_types import Agent, AgentCapabilities
from pddl_generalized_allocator.utils.errors import ModelBuildError


def _infer_agent_type_from_agents(
    task: PlanningTask,
    agents: List[Agent],
) -> Optional[str]:
    """
    エージェント名に対応するオブジェクトの型から agent_type を推論する。

    ルール:
      - agent 名と同じ名前を持つオブジェクトを探す
      - その type を集める
      - 1種類であればそれを agent_type とする
      - 0種類なら None を返す（型なし）
      - 2種類以上ならエラー（複数 agent 型は当面サポートしない）
    """
    types: set[str] = set()
    for agent in agents:
        if agent.name not in task.objects:
            raise ModelBuildError(
                f"Agent '{agent.name}' not found in problem objects."
            )
        obj: Object = task.objects[agent.name]
        if obj.type is not None:
            types.add(obj.type)

    if len(types) == 0:
        # 全て untyped の場合は None（あとで「全パラメータ候補」扱いなどにできる）
        return None
    if len(types) > 1:
        raise ModelBuildError(
            f"Multiple agent types inferred from objects: {types}. "
            "Currently only a single agent type is supported."
        )
    return next(iter(types))


def build_capabilities(
    task: PlanningTask,
    agents: List[Agent],
) -> Dict[str, AgentCapabilities]:
    """
    各エージェントに対して、実行可能なアクション名集合を求める。

    前提:
      - エージェント名は problem の :agents、または :objects のオブジェクト名と一致する
      - オブジェクト側に型が設定されている場合、それが「agent 型」を表す
      - アクションスキーマのパラメータに agent 型の引数があるアクションは、
        その agent 型を持つ全エージェントが実行可能とみなす

    返り値:
      - agent_name -> AgentCapabilities
    """
    # 1. エージェント型を推論
    agent_type = _infer_agent_type_from_agents(task, agents)

    # 2. agent 型パラメータを持つアクションを特定
    #    action_name -> True (agent パラメータあり) のようにマークする
    actions_with_agent_param: Dict[str, bool] = {}

    for action_name, action in task.actions.items():
        if _action_has_agent_param(action, agent_type):
            actions_with_agent_param[action_name] = True

    # 3. 各エージェントの Capabilities を構築
    capabilities: Dict[str, AgentCapabilities] = {}
    for agent in agents:
        cap_actions = set(actions_with_agent_param.keys())
        capabilities[agent.name] = AgentCapabilities(
            agent=agent,
            actions=cap_actions,
        )

    return capabilities


def _action_has_agent_param(action: ActionSchema, agent_type: Optional[str]) -> bool:
    """
    アクションスキーマが「agent パラメータ」を持つか判定する。

    - agent_type が None の場合:
        -> 型なし PDDL とみなし、全パラメータを agent 候補とみなす。
           （この場合、全アクションが agent 対応になり得るが、CoDMAP では
            基本的に agent に型が付いている前提なので、あまり問題にはならない想定）
    - agent_type が 'robot' など具体的な文字列の場合:
        -> parameters[i].type == agent_type のものがあれば True。
    """
    if agent_type is None:
        # 型が無い場合は、少なくとも1つパラメータがあれば agent パラメータありとみなす
        return len(action.parameters) > 0

    for param in action.parameters:
        if param.type == agent_type:
            return True
    return False


def _infer_agent_type_from_actions_and_objects(
    task: PlanningTask,
) -> Optional[str]:
    """
    :agents や agent 型が明示されていない場合に、「どの型を agent とみなすか」を
    ヒューリスティックに決める。

    優先順位:
      1. 各アクションの「先頭パラメータ」の型を使ってスコアリングする。
         - type_to_first_param_actions[t] = {その型が先頭パラメータで出るアクション集合}
         - type_to_objects[t] = その型を持つオブジェクト数
         - score = #first_param_actions * #objects
         → score 最大の t を agent_type とする。
      2. 先頭パラメータから何も決められない場合（例えば先頭がすべて untyped など）は、
         旧来の「全パラメータ」を使ったスコアリングで fallback する。
    """
    # 1. 先頭パラメータの型ごとのアクション集合
    type_to_first_actions: dict[str, set[str]] = defaultdict(set)
    # 2. 全パラメータの型ごとのアクション集合（fallback 用）
    type_to_any_actions: dict[str, set[str]] = defaultdict(set)

    for action_name, action in task.actions.items():
        # 先頭パラメータ
        if action.parameters:
            first_type = action.parameters[0].type
            if first_type is not None:
                type_to_first_actions[first_type].add(action_name)
        # 全パラメータ
        for param in action.parameters:
            if param.type is not None:
                type_to_any_actions[param.type].add(action_name)

    # 3. 型ごとのオブジェクト数
    type_to_objects: dict[str, int] = defaultdict(int)
    for obj in task.objects.values():
        if obj.type is not None:
            type_to_objects[obj.type] += 1

    # 4. 先頭パラメータ型から agent_type を決める
    best_type: Optional[str] = None
    best_score = 0
    for t, acts in type_to_first_actions.items():
        num_actions = len(acts)
        num_objs = type_to_objects.get(t, 0)
        if num_actions == 0 or num_objs == 0:
            continue
        score = num_actions * num_objs
        if score > best_score:
            best_score = score
            best_type = t

    if best_type is not None:
        return best_type

    # 5. fallback: 全パラメータでスコアリング（旧ロジック）
    best_type = None
    best_score = 0
    for t, acts in type_to_any_actions.items():
        num_actions = len(acts)
        num_objs = type_to_objects.get(t, 0)
        if num_actions == 0 or num_objs == 0:
            continue
        score = num_actions * num_objs
        if score > best_score:
            best_score = score
            best_type = t

    return best_type


def build_agents_and_capabilities_auto(
    task: PlanningTask,
    problem_ast: ProblemAST,
) -> tuple[list[Agent], dict[str, AgentCapabilities]]:
    """
    問題インスタンスから Agent と Capabilities を自動構築する。

    優先順位:
      1. ProblemAST.agents が非空なら、それを「明示的なエージェント」とみなす。
         → 既存の build_capabilities を使う。
      2. ProblemAST.agents が空なら、以下のヒューリスティックで agent_type を推定する:
         - _infer_agent_type_from_actions_and_objects で型名を決定
         - その型のオブジェクトをすべて Agent とみなす
         - 既存の build_capabilities で capabilities を構築
      3. それでも候補が見つからなければ、単一 dummy agent を作り、
         全アクションを実行可能とする。
    """
    # 1. 明示的な :agents がある場合
    if problem_ast.agents:
        agents = [Agent(name) for name in problem_ast.agents]
        caps = build_capabilities(task, agents)
        return agents, caps

    # 2. agent_type を自動推定して、その型を持つオブジェクトを Agent にする
    agent_type = _infer_agent_type_from_actions_and_objects(task)

    if agent_type is not None:
        # 該当型のオブジェクトを Agent にする
        agent_objs: list[str] = [
            obj.name for obj in task.objects.values() if obj.type == agent_type
        ]
        if agent_objs:
            agents = [Agent(name) for name in agent_objs]
            caps = build_capabilities(task, agents)
            return agents, caps

    # 3. それでもダメなら fallback: dummy 単一エージェント
    dummy = Agent("agent0")
    # すべてのアクションを実行可能とする
    caps = {
        dummy.name: AgentCapabilities(
            agent=dummy,
            actions=set(task.actions.keys()),
        )
    }
    return [dummy], caps
