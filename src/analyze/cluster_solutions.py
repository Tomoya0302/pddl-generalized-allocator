#!/usr/bin/env python3
"""
階層的クラスタリング分析のCLIツール
"""
import argparse
import sys
from pathlib import Path

try:
    from .hierarchical_clustering import run_clustering_analysis
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from src.analyze.hierarchical_clustering import run_clustering_analysis


def main():
    parser = argparse.ArgumentParser(
        description='Perform hierarchical clustering analysis of PDDL solutions'
    )
    parser.add_argument(
        '--config',
        required=True,
        help='Configuration file for clustering analysis'
    )
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        sys.exit(1)
    
    try:
        print("🚀 Starting hierarchical clustering analysis...")
        results = run_clustering_analysis(str(config_path))
        
        print("\n🎉 Analysis completed successfully!")
        print(f"📊 Results summary:")
        print(f"   Solutions analyzed: {len(results['solution_names'])}")
        print(f"   Features used: {len(results['feature_names'])}")
        print(f"   Clusters found: {results['n_clusters']}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()