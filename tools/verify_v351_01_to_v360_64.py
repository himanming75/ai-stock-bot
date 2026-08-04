from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v351_01_to_v360_64/actual/latest_paper_order_proposal.json"
with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

proposal = result.get("proposal", {})
approval = result.get("approval", {})
audit = result.get("final_safety_audit", {})
checks = {
    "stage": result.get("stage") == "V360.64",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {"PAPER_ORDER_PROPOSAL_AWAITING_APPROVAL", "PAPER_ORDER_PROPOSAL_BLOCKED"},
    "proposal_present": bool(proposal),
    "approval_token_present": isinstance(approval.get("approval_token"), str) and len(approval.get("approval_token")) == 64,
    "approval_default_false": approval.get("approved") is False,
    "proposal_submission_false": proposal.get("submission_allowed") is False,
    "paper_endpoint_only": proposal.get("paper_endpoint_only") is True,
    "paper_submission_disabled": audit.get("paper_submission_enabled") is False,
    "live_submission_disabled": audit.get("live_submission_enabled") is False,
    "broker_write_disabled": audit.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "hash_present": isinstance(result.get("proposal_hash"), str) and len(result.get("proposal_hash")) == 64,
}
verification = {
    "verification_stage": "V360.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
