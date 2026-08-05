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
from execution_authorization.release_token import create_release_token
from execution_authorization.release_token_guard import run_release_token_gate

parser = argparse.ArgumentParser()
parser.add_argument(
    "--release-result",
    default="release/v392_06a/actual/queue_release_authorization_result.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_07a/actual/consumed_release_token_registry.json",
)
parser.add_argument(
    "--token-output",
    default="release/v392_07a/actual/release_token.json",
)
parser.add_argument(
    "--output",
    default="release/v392_07a/actual/release_token_gate_result.json",
)
args = parser.parse_args()

release_result = read_json(ROOT / args.release_result)

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"consumed_release_token_ids": []}

consumed = set(registry.get("consumed_release_token_ids", []))
secret = "LOCAL_ONLY_V392_07A_RELEASE_TOKEN_SECRET"

issued_at = datetime.now(timezone.utc)
expires_at = issued_at + timedelta(minutes=5)

release_token = create_release_token(
    release_result=release_result,
    secret=secret,
    issued_at=issued_at.isoformat(),
    expires_at=expires_at.isoformat(),
    nonce=secrets.token_hex(16),
)

result = run_release_token_gate(
    release_result=release_result,
    release_token=release_token,
    secret=secret,
    consumed_release_token_ids=consumed,
)

if result["release_token_gate_allowed"]:
    consumed.add(release_token["release_token_id"])

write_json(ROOT / args.token_output, release_token)
write_json(
    registry_path,
    {"consumed_release_token_ids": sorted(consumed)},
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_07a/actual/release_token_gate_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
