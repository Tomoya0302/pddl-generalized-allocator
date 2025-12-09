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


def create_diverse_configs(base_config_path: str, num_solutions: int, output_dir: str) -> List[str]:
    """多様な設定ファイルを生成"""
    
    # ベース設定を読み込み
    with open(base_config_path, 'r') as f:
        base_config = yaml.safe_load(f)
    
    config_files = []
    strategies = ['minimize_subtasks', 'balanced', 'distribute_goals', 'auto']
    
    for i in range(num_solutions):
        # 設定をコピー
        config = base_config.copy()
        
        # 多様性のための設定調整
        seed = 42 + i * 123  # 異なるseedを生成
        strategy = strategies[i % len(strategies)]
        
        # クラスタリング設定を調整
        config['clustering']['random_seed'] = seed
        config['clustering']['optimization_strategy'] = strategy
        config['clustering']['strategy_randomness'] = 0.1 + (i % 5) * 0.1  # 0.1-0.5の範囲
        
        # より多様性を持たせるための追加調整（制約範囲内で）
        base_max_subtasks = base_config['clustering']['max_subtasks']
        base_max_goals = base_config['clustering'].get('max_goals_per_subtask', 10)
        
        if i % 4 == 0:  # サブタスク数を抑える設定
            config['clustering']['max_subtasks'] = max(base_max_subtasks - 10, int(base_max_subtasks * 0.7))
        elif i % 4 == 1:  # サブタスク数を少し増やす設定
            config['clustering']['max_subtasks'] = min(base_max_subtasks + 5, int(base_max_subtasks * 1.2))
        elif i % 4 == 2:  # ゴール数を制限
            config['clustering']['max_goals_per_subtask'] = max(base_max_goals - 3, int(base_max_goals * 0.8))
        else:  # ゴール数を少し増やす
            config['clustering']['max_goals_per_subtask'] = min(base_max_goals + 3, int(base_max_goals * 1.3))
        
        # epsilonの調整で探索の多様性を変える
        if i % 3 == 0:
            config['clustering']['epsilon_start'] = 0.0
            config['clustering']['epsilon_step'] = 0.1
        elif i % 3 == 1:
            config['clustering']['epsilon_start'] = 0.1
            config['clustering']['epsilon_step'] = 0.3
        else:
            config['clustering']['epsilon_start'] = 0.2
            config['clustering']['epsilon_step'] = 0.2
        
        # ランドマーク使用の調整
        config['clustering']['use_landmarks'] = (i % 2 == 0)
        config['clustering']['landmark_max_depth'] = 2 + (i % 3)
        
        # 設定ファイルを保存
        config_file = os.path.join(output_dir, f'diverse_config_{i:03d}.yaml')
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        config_files.append(config_file)
    
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
        print(f"⚙️  Running solution {i+1}/{args.num_solutions}: {os.path.basename(config_file)} (timeout: {timeout}s)")
        
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