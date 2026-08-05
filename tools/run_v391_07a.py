from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from autonomous_risk_governor.kill_switch_guard import run_guard

parser = argparse.ArgumentParser()
parser.add_argument(
    "--policy-result",
    default="release/v391_01a/actual/risk_policy_validation_result.json",
)
parser.add_argument(
    "--control",
    default="release/v391_07a/fixtures/sample_kill_switch_control.json",
)
parser.add_argument(
    "--output",
    default="release/v391_07a/actual/kill_switch_guard_result.json",
)
args = parser.parse_args()

result = run_guard(
    read_json(ROOT / args.policy_result),
    read_json(ROOT / args.control),
)

write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v391_07a/actual/kill_switch_ledger.jsonl",
    result,
)
print(json.dumps(result, indent=2, sort_keys=True))
