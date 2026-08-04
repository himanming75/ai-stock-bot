from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from governed_decision_bridge.io import read_json
from governed_decision_bridge.replay import verify_replay

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="release/v341_01_to_v350_64/actual/latest_governed_decision.json")
args = parser.parse_args()
result = verify_replay(read_json(ROOT / args.input))
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["valid"] else 1)
