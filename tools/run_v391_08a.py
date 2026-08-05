from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.auto_pause_guard import run_guard
from autonomous_risk_governor.io import append_jsonl, read_json, write_json

parser = argparse.ArgumentParser()
parser.add_argument(
    "--policy-result",
    default="release/v391_01a/actual/risk_policy_validation_result.json",
)
parser.add_argument(
    "--guard-results",
    default="release/v391_08a/fixtures/sample_guard_results.json",
)
parser.add_argument(
    "--output",
    default="release/v391_08a/actual/auto_pause_guard_result.json",
)
args = parser.parse_args()

payload = read_json(ROOT / args.guard_results)
guard_results = payload.get("guard_results", {})

result = run_guard(
    read_json(ROOT / args.policy_result),
    guard_results,
)

write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v391_08a/actual/auto_pause_ledger.jsonl",
    result,
)
print(json.dumps(result, indent=2, sort_keys=True))
