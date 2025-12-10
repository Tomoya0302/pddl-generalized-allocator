import argparse
from .runner import run_volume_analysis

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()

    run_volume_analysis(args.config)

if __name__ == "__main__":
    main()