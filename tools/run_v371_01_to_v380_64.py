from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_execution_lifecycle.engine import run

parser = argparse.ArgumentParser()
parser.add_argument("--allow-paper-network", action="store_true")
args = parser.parse_args()

result = run(ROOT, allow_network=args.allow_paper_network)
print(json.dumps(result, indent=2, sort_keys=True))
