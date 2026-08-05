from __future__ import annotations
from datetime import datetime, timezone, timedelta
import argparse
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from execution_authorization.token_gate import create_token
from execution_authorization.token_gate_runner import run_token_gate

parser = argparse.ArgumentParser()
parser.add_argument(
    "--authorization-result",
    default="release/v392_01a/actual/execution_authorization_result.json",
)
parser.add_argument(
    "--proposal",
    default="release/v392_01a/fixtures/sample_proposal.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_02a/actual/consumed_token_registry.json",
)
parser.add_argument(
    "--token-output",
    default="release/v392_02a/actual/authorization_token.json",
)
parser.add_argument(
    "--output",
    default="release/v392_02a/actual/authorization_token_gate_result.json",
)
args = parser.parse_args()

authorization_result = read_json(ROOT / args.authorization_result)
proposal = read_json(ROOT / args.proposal)

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"consumed_token_ids": []}

consumed = set(registry.get("consumed_token_ids", []))
secret = "LOCAL_ONLY_V392_02A_TEST_SECRET"

issued = datetime.now(timezone.utc)
expires = issued + timedelta(minutes=5)
token = create_token(
    authorization_result=authorization_result,
    proposal=proposal,
    secret=secret,
    issued_at=issued.isoformat(),
    expires_at=expires.isoformat(),
    nonce=secrets.token_hex(16),
)

result = run_token_gate(
    authorization_result=authorization_result,
    proposal=proposal,
    token=token,
    secret=secret,
    consumed_token_ids=consumed,
)

if result["token_gate_allowed"]:
    consumed.add(token["token_id"])

write_json(ROOT / args.token_output, token)
write_json(registry_path, {"consumed_token_ids": sorted(consumed)})
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_02a/actual/authorization_token_gate_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
