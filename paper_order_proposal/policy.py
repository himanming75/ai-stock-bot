from __future__ import annotations
from pathlib import Path
from .io import read_json


POLICY_PATH = Path("release/v351_01_to_v360_64/config/paper_order_proposal_policy.json")


def load(root: Path) -> dict:
    return read_json(root / POLICY_PATH)


def validate(policy: dict) -> dict:
    checks = {
        "proposal_mode": policy.get("mode") == "PAPER_ORDER_PROPOSAL_ONLY",
        "paper_endpoint_only": policy.get("paper_endpoint_only") is True,
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
        "maximum_new_orders_zero": int(policy.get("maximum_new_orders_per_day", -1)) == 0,
        "approval_required": policy.get("approval_required") is True,
        "kill_switch_required": policy.get("kill_switch_required") is True,
    }
    return {"valid": all(checks.values()), "checks": checks, "failed": [k for k, v in checks.items() if not v]}
