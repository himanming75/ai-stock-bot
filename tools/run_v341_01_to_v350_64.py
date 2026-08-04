from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from governed_decision_bridge.engine import build_decision
from governed_decision_bridge.io import append_jsonl, read_json, write_json

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="release/v341_01_to_v350_64/fixtures/sample_decision_context.json")
parser.add_argument("--output", default="release/v341_01_to_v350_64/actual/latest_governed_decision.json")
parser.add_argument("--no-ledger", action="store_true")
args = parser.parse_args()

payload = read_json(ROOT / args.input)
result = build_decision(payload)
write_json(ROOT / args.output, result)
if not args.no_ledger:
    append_jsonl(ROOT / "release/v341_01_to_v350_64/actual/governed_decision_ledger.jsonl", result)
print(json.dumps(result, indent=2, sort_keys=True))
