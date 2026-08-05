from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.concentration_guard import run_guard
from autonomous_risk_governor.io import append_jsonl, read_json, write_json

parser = argparse.ArgumentParser()
parser.add_argument(
    "--policy-result",
    default="release/v391_01a/actual/risk_policy_validation_result.json",
)
parser.add_argument(
    "--account",
    default="release/v391_06a/fixtures/sample_account.json",
)
parser.add_argument(
    "--positions",
    default="release/v391_06a/fixtures/sample_positions.json",
)
parser.add_argument(
    "--proposal",
    default="release/v391_06a/fixtures/sample_proposal.json",
)
parser.add_argument(
    "--output",
    default="release/v391_06a/actual/symbol_concentration_guard_result.json",
)
args = parser.parse_args()

positions_payload = read_json(ROOT / args.positions)
positions = positions_payload.get("positions", [])

result = run_guard(
    read_json(ROOT / args.policy_result),
    read_json(ROOT / args.account),
    positions,
    read_json(ROOT / args.proposal),
)

write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v391_06a/actual/symbol_concentration_ledger.jsonl",
    result,
)
print(json.dumps(result, indent=2, sort_keys=True))
