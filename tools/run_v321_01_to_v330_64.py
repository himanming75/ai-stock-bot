from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from long_run_qualification.qualifier import qualify
from long_run_qualification.runner import run

parser = argparse.ArgumentParser()
parser.add_argument("--allow-paper-network", action="store_true")
parser.add_argument("--no-sleep", action="store_true")
parser.add_argument("--analyze-only", action="store_true")
args = parser.parse_args()
result = qualify(ROOT) if args.analyze_only else run(ROOT, allow_network=args.allow_paper_network, sleep_enabled=not args.no_sleep)
print(json.dumps(result, indent=2, sort_keys=True))
