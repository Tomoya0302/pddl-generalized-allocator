#!/usr/bin/env python3
"""
多目的最適化結果の分析スクリプト
"""
import json
import sys
from collections import Counter

def analyze_subtask_distribution(subtasks):
    """サブタスクのゴール分散を分析"""
    goal_counts = [len(subtask['goals']) for subtask in subtasks]
    total_goals = sum(goal_counts)
    
    return {
        'total_subtasks': len(subtasks),
        'total_goals': total_goals,
        'goal_counts': goal_counts,
        'avg_goals_per_subtask': total_goals / len(subtasks) if subtasks else 0,
        'min_goals': min(goal_counts) if goal_counts else 0,
        'max_goals': max(goal_counts) if goal_counts else 0,
        'goal_distribution': dict(Counter(goal_counts))
    }

def analyze_agent_workload(assignment):
    """エージェントの作業負荷を分析"""
    agent_counts = Counter(assignment.values())
    return dict(agent_counts)

def analyze_role_signatures(subtasks):
    """role_signatureの多様性を分析"""
    signatures = []
    for subtask in subtasks:
        role_sig = subtask['role_signature']
        # role_signatureを文字列に変換
        sig_str = f"{role_sig}"
        signatures.append(sig_str)
    
    unique_signatures = len(set(signatures))
    return {
        'total_signatures': len(signatures),
        'unique_signatures': unique_signatures,
        'signature_diversity': unique_signatures / len(signatures) if signatures else 0
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <result_file1> [result_file2] ...")
        sys.exit(1)
    
    results = {}
    
    for file_path in sys.argv[1:]:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            subtasks = data['subtasks']
            assignment = data['assignment']
            
            analysis = {
                'file': file_path,
                'distribution': analyze_subtask_distribution(subtasks),
                'workload': analyze_agent_workload(assignment),
                'role_diversity': analyze_role_signatures(subtasks)
            }
            
            results[file_path] = analysis
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            continue
    
    # 結果を表示
    print("=" * 80)
    print("MULTI-OBJECTIVE OPTIMIZATION RESULTS ANALYSIS")
    print("=" * 80)
    
    for file_path, analysis in results.items():
        print(f"\n📁 FILE: {file_path}")
        print("-" * 50)
        
        dist = analysis['distribution']
        print(f"📊 SUBTASK DISTRIBUTION:")
        print(f"   Total Subtasks: {dist['total_subtasks']}")
        print(f"   Total Goals: {dist['total_goals']}")
        print(f"   Average Goals/Subtask: {dist['avg_goals_per_subtask']:.2f}")
        print(f"   Min-Max Goals: {dist['min_goals']}-{dist['max_goals']}")
        print(f"   Goal Distribution: {dist['goal_distribution']}")
        
        print(f"\n👥 AGENT WORKLOAD:")
        for agent, count in sorted(analysis['workload'].items()):
            print(f"   {agent}: {count} subtasks")
        
        print(f"\n🔧 ROLE DIVERSITY:")
        role_div = analysis['role_diversity']
        print(f"   Total Signatures: {role_div['total_signatures']}")
        print(f"   Unique Signatures: {role_div['unique_signatures']}")
        print(f"   Diversity Ratio: {role_div['signature_diversity']:.2f}")
    
    # 比較分析
    if len(results) > 1:
        print("\n" + "=" * 80)
        print("COMPARATIVE ANALYSIS")
        print("=" * 80)
        
        files = list(results.keys())
        for i, file1 in enumerate(files):
            for file2 in files[i+1:]:
                print(f"\n🔍 COMPARING {file1} vs {file2}:")
                
                dist1 = results[file1]['distribution']
                dist2 = results[file2]['distribution']
                
                print(f"   Subtask Count: {dist1['total_subtasks']} vs {dist2['total_subtasks']}")
                print(f"   Avg Goals/Subtask: {dist1['avg_goals_per_subtask']:.2f} vs {dist2['avg_goals_per_subtask']:.2f}")
                print(f"   Max Goals: {dist1['max_goals']} vs {dist2['max_goals']}")
                
                # ゴール分散の比較
                import math
                def variance(counts):
                    if not counts:
                        return 0
                    mean = sum(counts) / len(counts)
                    return sum((x - mean) ** 2 for x in counts) / len(counts)
                
                var1 = variance(dist1['goal_counts'])
                var2 = variance(dist2['goal_counts'])
                print(f"   Goal Variance: {var1:.2f} vs {var2:.2f}")

if __name__ == "__main__":
    main()