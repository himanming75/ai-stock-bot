from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.integration_guard import run_guard
from autonomous_risk_governor.io import append_jsonl, read_json, write_json

parser = argparse.ArgumentParser()
parser.add_argument(
    "--inputs",
    default="release/v391_10a/fixtures/sample_integration_inputs.json",
)
parser.add_argument(
    "--output",
    default="release/v391_10a/actual/risk_governor_integration_result.json",
)
args = parser.parse_args()

payload = read_json(ROOT / args.inputs)
results = payload.get("results", {})

result = run_guard(results)

write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v391_10a/actual/risk_governor_integration_ledger.jsonl",
    result,
)
print(json.dumps(result, indent=2, sort_keys=True))
