

"""
Entry point for the pipeline.
Usage:
  python -m scripts.run_pipeline --drug aspirin --limit 50
"""

import argparse
from orchestrator.orchestrator import Orchestrator

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drug", required=True, help="Drug name to query OpenFDA")
    parser.add_argument("--limit", type=int, default=100, help="Max events to fetch")
    args = parser.parse_args()

    orch = Orchestrator()
    trace = orch.run(args.drug, args.limit)
    import json
    print("Pipeline finished. Trace summary:")
    print(json.dumps(trace, indent=2))

if __name__ == "__main__":
    main()
