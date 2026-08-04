from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.daily_loss_guard import run_guard
from autonomous_risk_governor.io import read_json, write_json

parser = argparse.ArgumentParser()
parser.add_argument(
    "--policy-result",
    default="release/v391_01a/actual/risk_policy_validation_result.json",
)
parser.add_argument(
    "--account",
    default="release/v391_02a/fixtures/sample_account.json",
)
parser.add_argument(
    "--output",
    default="release/v391_02a/actual/daily_loss_guard_result.json",
)
args = parser.parse_args()

result = run_guard(
    read_json(ROOT / args.policy_result),
    read_json(ROOT / args.account),
)
write_json(ROOT / args.output, result)
print(json.dumps(result, indent=2, sort_keys=True))
