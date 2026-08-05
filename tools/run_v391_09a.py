from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from autonomous_risk_governor.manual_resume_guard import run_guard

parser = argparse.ArgumentParser()
parser.add_argument(
    "--policy-result",
    default="release/v391_01a/actual/risk_policy_validation_result.json",
)
parser.add_argument(
    "--pause-result",
    default="release/v391_09a/fixtures/sample_pause_result.json",
)
parser.add_argument(
    "--kill-switch-result",
    default="release/v391_09a/fixtures/sample_kill_switch_result.json",
)
parser.add_argument(
    "--request",
    default="release/v391_09a/fixtures/sample_manual_resume_request.json",
)
parser.add_argument(
    "--output",
    default="release/v391_09a/actual/manual_resume_guard_result.json",
)
args = parser.parse_args()

result = run_guard(
    read_json(ROOT / args.policy_result),
    read_json(ROOT / args.pause_result),
    read_json(ROOT / args.kill_switch_result),
    read_json(ROOT / args.request),
)

write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v391_09a/actual/manual_resume_ledger.jsonl",
    result,
)
print(json.dumps(result, indent=2, sort_keys=True))
