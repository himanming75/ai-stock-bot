from __future__ import annotations
import argparse
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from execution_authorization.dispatch_preparation import (
    build_order_payload,
    canonical_hash,
)
from execution_authorization.dispatch_preparation_guard import (
    run_dispatch_preparation,
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--token-gate-result",
    default="release/v392_02a/actual/authorization_token_gate_result.json",
)
parser.add_argument(
    "--proposal",
    default="release/v392_01a/fixtures/sample_proposal.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_03a/actual/dispatch_queue_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_03a/actual/dispatch_preparation_result.json",
)
args = parser.parse_args()

token_gate_result = read_json(ROOT / args.token_gate_result)
proposal = read_json(ROOT / args.proposal)

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"queued_dispatch_ids": []}

queued = set(registry.get("queued_dispatch_ids", []))
order_payload = build_order_payload(proposal)

dispatch_request = {
    "dispatch_id": f"dispatch-{secrets.token_hex(12)}",
    "token_id": token_gate_result.get("token_id"),
    "proposal_id": proposal.get("proposal_id"),
    "policy_hash": token_gate_result.get("authorization_result", {}).get("policy_hash"),
    "order_payload_hash": canonical_hash(order_payload),
    "target_environment": "PAPER",
    "broker_submission_enabled": False,
    "automatic_dispatch": False,
}

result = run_dispatch_preparation(
    token_gate_result=token_gate_result,
    proposal=proposal,
    dispatch_request=dispatch_request,
    queued_dispatch_ids=queued,
)

if result["queue_entry_allowed"]:
    queued.add(result["evaluation"]["dispatch_id"])

write_json(
    registry_path,
    {"queued_dispatch_ids": sorted(queued)},
)
write_json(
    ROOT / "release/v392_03a/actual/dispatch_request.json",
    dispatch_request,
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_03a/actual/dispatch_preparation_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
