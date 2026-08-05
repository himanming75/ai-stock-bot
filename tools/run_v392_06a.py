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
from execution_authorization.queue_release import (
    REQUIRED_APPROVAL_PHRASE,
    canonical_hash,
)
from execution_authorization.queue_release_guard import (
    run_queue_release_authorization,
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--inspection-result",
    default="release/v392_05a/actual/queue_inspection_gate_result.json",
)
parser.add_argument(
    "--queue-state",
    default="release/v392_04a/actual/dispatch_queue_state.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_06a/actual/consumed_release_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_06a/actual/queue_release_authorization_result.json",
)
args = parser.parse_args()

inspection_result = read_json(ROOT / args.inspection_result)
queue_state = read_json(ROOT / args.queue_state)

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"consumed_release_ids": []}

consumed = set(registry.get("consumed_release_ids", []))
head = queue_state.get("entries", [])[0]
inspection_eval = inspection_result.get("evaluation", {})

release_request = {
    "release_id": f"release-{secrets.token_hex(12)}",
    "dispatch_id": head.get("dispatch_id"),
    "token_id": head.get("token_id"),
    "proposal_id": head.get("proposal_id"),
    "queue_hash": canonical_hash(queue_state),
    "head_entry_hash": canonical_hash(head),
    "approval_phrase": REQUIRED_APPROVAL_PHRASE,
    "approved_by": "local-queue-release-operator",
    "reason": "FIFO head inspected and approved for local release-token preparation.",
    "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    "target_environment": "PAPER",
    "automatic_release": False,
    "dispatch_execution_enabled": False,
}

result = run_queue_release_authorization(
    inspection_result=inspection_result,
    queue_state=queue_state,
    release_request=release_request,
    consumed_release_ids=consumed,
)

if result["queue_release_authorized"]:
    consumed.add(release_request["release_id"])

write_json(
    ROOT / "release/v392_06a/actual/queue_release_request.json",
    release_request,
)
write_json(
    registry_path,
    {"consumed_release_ids": sorted(consumed)},
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_06a/actual/queue_release_authorization_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
