from __future__ import annotations
from pathlib import Path
from .io import read_json


POLICY = Path("release/v331_01_to_v340_64/config/observation_governance_policy.json")


def load(root: Path) -> dict:
    return read_json(root / POLICY)


def validate(policy: dict) -> dict:
    checks = {
        "governance_enabled": policy.get("governance_enabled") is True,
        "monitor_only": policy.get("monitor_only") is True,
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
        "paper_endpoint_only": policy.get("paper_endpoint_only") is True,
        "maximum_new_orders_zero": int(policy.get("maximum_new_orders_per_day", -1)) == 0,
        "qualification_required": policy.get("required_qualification_state") == "REAL_PAPER_LONG_RUN_QUALIFIED",
    }
    return {"valid": all(checks.values()), "checks": checks, "failed": [k for k, v in checks.items() if not v]}
