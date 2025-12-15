#!/usr/bin/env python3
"""
多様なサブタスク分解解を自動生成するCLIツール
"""
import argparse
import os
import json
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
import yaml

BASE_FEATURE_OBJECTIVES = [
    {"name": "subtask_count",               "direction": "min"},
    {"name": "goal_mean",                   "direction": "min"},
    {"name": "goal_variance",               "direction": "max"},
    {"name": "goal_min",                    "direction": "max"},
    {"name": "goal_max",                    "direction": "min"},
    {"name": "goal_range",                  "direction": "max"},

    {"name": "num_active_agents",           "direction": "max"},
    {"name": "agent_balance_variance",      "direction": "min"},
    {"name": "agent_balance_max_min_ratio", "direction": "min"},

    {"name": "unique_role_signature_count", "direction": "max"},
    {"name": "role_signature_entropy",      "direction": "max"},
    {"name": "avg_role_attributes_per_subtask", "direction": "max"},
    {"name": "complex_role_ratio",          "direction": "max"},
    {"name": "avg_role_complexity",         "direction": "max"},

    {"name": "avg_subtask_similarity",      "direction": "min"},
    {"name": "similarity_variance",         "direction": "max"},
]

def build_feature_objectives_for_solution(i: int) -> list[dict]:
    """
    解インデックス i に対して、
      1周目 (round=1): 1特徴量・順方向
      2周目 (round=2): 1特徴量・方向反転
      3周目 (round=3): 2特徴量・順方向
      4周目 (round=4): 2特徴量・方向反転
      5周目 (round=5): 3特徴量・順方向
      6周目 (round=6): 3特徴量・方向反転
      ...
    というルールで [{name, direction, weight}, ...] を返す。
    """
    n = len(BASE_FEATURE_OBJECTIVES)
    if n == 0:
        return []

    round_index = i // n           # 0,1,2,...
    round_num = round_index + 1    # 1,2,3,...

    base_idx = i % n               # 0..n-1

    # 使う特徴量の個数： 1,1,2,2,3,3,4,4,...
    combo_size = (round_num + 1) // 2

    # 偶数ラウンドなら方向反転
    flip_direction = (round_num % 2 == 0)

    # base_idx から combo_size 個の特徴量をリング状に選ぶ
    indices = [(base_idx + offset) % n for offset in range(combo_size)]
    weight = 1.0 / combo_size

    objectives: list[dict] = []
    for idx in indices:
        base = BASE_FEATURE_OBJECTIVES[idx]
        base_dir = base["direction"]
        if flip_direction:
            direction = "max" if base_dir == "min" else "min"
        else:
            direction = base_dir

        objectives.append(
            {
                "name": base["name"],
                "direction": direction,
                "weight": weight,
            }
        )

    return objectives

def create_diverse_configs(base_config_path: str, num_solutions: int, output_dir: str) -> list[str]:
    with open(base_config_path, "r") as f:
        base_config = yaml.safe_load(f)

    config_files: list[str] = []

    for i in range(num_solutions):
        config = yaml.safe_load(yaml.dump(base_config))  # deep copy

        # 乱数シードなどは今までどおり
        seed = 42 + i * 123
        config["clustering"]["random_seed"] = seed

        # ★ 解 i 用の feature objectives を決定
        objectives = build_feature_objectives_for_solution(i)
        config["clustering"]["optimization_strategy"] = "feature_driven"
        config["clustering"]["feature_objectives"] = objectives

        # epsilon / max_subtasks / use_landmarks などは従来のロジックで揺らす
        # （ここは既存コードをそのまま残す）

        out_path = os.path.join(output_dir, f"diverse_config_{i:03d}.yaml")
        with open(out_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)

        config_files.append(out_path)
        print(f"  -> config {out_path} (objectives={objectives})")

    return config_files


def run_main_with_config(config_file: str, output_file: str, timeout: int = 120) -> Dict[str, Any]:
    """main.pyを呼び出して結果を取得（タイムアウト付き）"""
    try:
        # main.pyを実行
        cmd = [sys.executable, '-m', 'src.cli.main', '--config', config_file, '--output', output_file]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd(), timeout=timeout)
        
        if result.returncode != 0:
            # エラーの種類を判定して簡潔なメッセージを出力
            error_msg = result.stderr.strip()
            if "Cannot satisfy max_subtasks=" in error_msg and "even after" in error_msg:
                # max_subtasks制約違反エラーの場合
                print(f"🚫 Constraint failure: Skipping config {os.path.basename(config_file)} (max_subtasks not satisfiable)")
            elif "RuntimeError" in error_msg:
                # その他のRuntimeErrorの場合
                print(f"❌ Runtime error: Skipping config {os.path.basename(config_file)}")
            else:
                # その他のエラーの場合
                print(f"⚠️  Error: Skipping config {os.path.basename(config_file)}")
            return None
        
        # 結果ファイルを読み込み
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                return json.load(f)
        else:
            print(f"Warning: Output file {output_file} not found")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout ({timeout}s): Skipping config {config_file}")
        return None
    except Exception as e:
        print(f"❌ Error running config {config_file}: {e}")
        return None


def analyze_solution_diversity(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """解の多様性を分析"""
    if not results:
        return {}
    
    analysis = {
        'total_solutions': len(results),
        'subtask_counts': [],
        'goal_distributions': [],
        'agent_workloads': [],
        'strategies_used': [],
        'diversity_metrics': {}
    }
    
    for i, result in enumerate(results):
        if result is None:
            continue
            
        subtasks = result.get('subtasks', [])
        assignment = result.get('assignment', {})
        
        # サブタスク数
        subtask_count = len(subtasks)
        analysis['subtask_counts'].append(subtask_count)
        
        # ゴール分布
        goal_counts = [len(subtask['goals']) for subtask in subtasks]
        analysis['goal_distributions'].append({
            'counts': goal_counts,
            'avg': sum(goal_counts) / len(goal_counts) if goal_counts else 0,
            'min': min(goal_counts) if goal_counts else 0,
            'max': max(goal_counts) if goal_counts else 0
        })
        
        # エージェント作業負荷
        from collections import Counter
        agent_counts = Counter(assignment.values())
        analysis['agent_workloads'].append(dict(agent_counts))
    
    # 多様性指標
    if analysis['subtask_counts']:
        analysis['diversity_metrics'] = {
            'subtask_count_range': [min(analysis['subtask_counts']), max(analysis['subtask_counts'])],
            'subtask_count_variance': _variance(analysis['subtask_counts']),
            'unique_subtask_counts': len(set(analysis['subtask_counts'])),
            'avg_goal_variance': _avg_goal_variance(analysis['goal_distributions'])
        }
    
    return analysis


def _variance(values: List[float]) -> float:
    """分散を計算"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


def _avg_goal_variance(distributions: List[Dict[str, Any]]) -> float:
    """ゴール分布の平均分散"""
    if not distributions:
        return 0.0
    
    variances = []
    for dist in distributions:
        counts = dist['counts']
        if len(counts) > 1:
            variances.append(_variance(counts))
    
    return sum(variances) / len(variances) if variances else 0.0


def save_analysis_report(analysis: Dict[str, Any], output_dir: str):
    """分析レポートを保存"""
    report_file = os.path.join(output_dir, 'diversity_analysis.json')
    with open(report_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    # 読みやすい要約レポートも作成
    summary_file = os.path.join(output_dir, 'diversity_summary.txt')
    with open(summary_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("DIVERSE SUBTASK DECOMPOSITION ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total Solutions Generated: {analysis['total_solutions']}\n")
        
        if analysis['diversity_metrics']:
            metrics = analysis['diversity_metrics']
            f.write(f"Subtask Count Range: {metrics['subtask_count_range'][0]}-{metrics['subtask_count_range'][1]}\n")
            f.write(f"Subtask Count Variance: {metrics['subtask_count_variance']:.2f}\n")
            f.write(f"Unique Subtask Counts: {metrics['unique_subtask_counts']}\n")
            f.write(f"Average Goal Distribution Variance: {metrics['avg_goal_variance']:.2f}\n")
        
        f.write("\nSubtask Count Distribution:\n")
        subtask_counts = analysis.get('subtask_counts', [])
        from collections import Counter
        count_dist = Counter(subtask_counts)
        for count, freq in sorted(count_dist.items()):
            f.write(f"  {count} subtasks: {freq} solutions\n")


def main():
    parser = argparse.ArgumentParser(description='Generate diverse subtask decomposition solutions')
    parser.add_argument('--config', required=True, help='Base configuration file')
    parser.add_argument('--num-solutions', type=int, default=10, help='Number of diverse solutions to generate')
    parser.add_argument('--output-dir', required=True, help='Output directory for results')
    
    args = parser.parse_args()
    
    # 出力ディレクトリを作成
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Generating {args.num_solutions} diverse subtask decomposition solutions...")
    print(f"📁 Base config: {args.config}")
    print(f"📂 Output directory: {args.output_dir}")
    
    # 多様な設定ファイルを生成
    print("\n📝 Creating diverse configuration files...")
    config_files = create_diverse_configs(args.config, args.num_solutions, str(output_dir))
    
    # ベース設定からタイムアウト値を読み込み
    with open(args.config, 'r') as f:
        base_config = yaml.safe_load(f)
    timeout = base_config.get('clustering', {}).get('solution_timeout', 120)
    
    # 各設定でmain.pyを実行
    results = []
    successful_runs = 0
    timeout_count = 0
    
    for i, config_file in enumerate(config_files):
        print(f"⚙️ Running solution {i+1}/{args.num_solutions}: {os.path.basename(config_file)} (timeout: {timeout}s)")
        try:
            with open(config_file, "r") as cf:
                cfg_for_log = yaml.safe_load(cf)

            clustering_cfg = (cfg_for_log or {}).get("clustering", {}) or {}

            feature_objs = clustering_cfg.get("feature_objectives")
            # 新方式: feature_objectives: [{name, direction, weight}, ...]
            if feature_objs:
                parts = []
                for obj in feature_objs:
                    name = obj.get("name")
                    direction = obj.get("direction")
                    weight = obj.get("weight", None)
                    if weight is not None:
                        parts.append(f"{name}({direction}, w={weight:.2f})")
                    else:
                        parts.append(f"{name}({direction})")
                print(f"   ↳ 使用特徴量: " + ", ".join(parts))

            else:
                # 互換性確保: 単一指定版 (feature_objective_name / direction) を使っている場合
                name = clustering_cfg.get("feature_objective_name")
                direction = clustering_cfg.get("feature_objective_direction")
                if name and direction:
                    print(f"   ↳ 使用特徴量: {name}({direction})")
                else:
                    # 何も設定されていない場合
                    pass
        except Exception as e:
            # ログ目的なので、失敗しても致命的にはしない
            print(f"   ↳ 使用特徴量: 取得に失敗しました ({e})")
        output_file = str(output_dir / f'result_{i:03d}.json')
        result = run_main_with_config(config_file, output_file, timeout)
        
        if result is not None:
            results.append(result)
            successful_runs += 1
            print(f"✅ Solution {i+1} completed successfully")
        else:
            results.append(None)
            # タイムアウトかエラーかを区別してカウント
            if os.path.exists(output_file):
                os.remove(output_file)  # 不完全なファイルを削除
            timeout_count += 1
    
    print(f"\n📊 GENERATION SUMMARY:")
    print(f"   ✅ Successfully generated: {successful_runs}/{args.num_solutions} solutions")
    if timeout_count > 0:
        print(f"   ⏰ Timed out or failed: {timeout_count} solutions")
    print(f"   🕒 Timeout setting: {timeout} seconds per solution")
    
    # 多様性分析
    print("📊 Analyzing solution diversity...")
    analysis = analyze_solution_diversity(results)
    
    # 分析レポートを保存
    save_analysis_report(analysis, str(output_dir))
    
    # 結果を表示
    if analysis.get('diversity_metrics'):
        metrics = analysis['diversity_metrics']
        print(f"\n🎯 DIVERSITY METRICS:")
        print(f"   Subtask Count Range: {metrics['subtask_count_range'][0]}-{metrics['subtask_count_range'][1]}")
        print(f"   Subtask Count Variance: {metrics['subtask_count_variance']:.2f}")
        print(f"   Unique Subtask Counts: {metrics['unique_subtask_counts']}")
        print(f"   Average Goal Variance: {metrics['avg_goal_variance']:.2f}")
    
    print(f"\n📁 Results saved to: {args.output_dir}")
    print(f"   - Individual solutions: result_XXX.json")
    print(f"   - Configuration files: diverse_config_XXX.yaml")
    print(f"   - Analysis report: diversity_analysis.json")
    print(f"   - Summary report: diversity_summary.txt")


if __name__ == '__main__':
    main()