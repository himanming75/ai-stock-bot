from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.drawdown_guard import run_guard
from autonomous_risk_governor.io import append_jsonl, read_json, write_json

parser = argparse.ArgumentParser()
parser.add_argument(
    "--policy-result",
    default="release/v391_01a/actual/risk_policy_validation_result.json",
)
parser.add_argument(
    "--account",
    default="release/v391_03a/fixtures/sample_account.json",
)
parser.add_argument(
    "--checkpoint",
    default="release/v391_03a/actual/drawdown_checkpoint.json",
)
parser.add_argument(
    "--output",
    default="release/v391_03a/actual/max_drawdown_guard_result.json",
)
args = parser.parse_args()

checkpoint_path = ROOT / args.checkpoint
if checkpoint_path.exists():
    checkpoint = read_json(checkpoint_path)
else:
    account = read_json(ROOT / args.account)
    checkpoint = {"peak_equity": account.get("equity")}

result = run_guard(
    read_json(ROOT / args.policy_result),
    read_json(ROOT / args.account),
    checkpoint,
)

write_json(ROOT / args.output, result)
write_json(checkpoint_path, {
    "stage": "V391.03A",
    "updated_at": result["observed_at"],
    "peak_equity": result["evaluation"]["updated_peak_equity"],
})
append_jsonl(
    ROOT / "release/v391_03a/actual/drawdown_ledger.jsonl",
    result,
)
print(json.dumps(result, indent=2, sort_keys=True))
