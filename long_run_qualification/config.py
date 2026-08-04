from __future__ import annotations
from pathlib import Path
from long_run_qualification.io import load_json

RELATIVE = Path("release/v321_01_to_v330_64/config/real_paper_long_run_policy.json")


def load(root: Path) -> dict:
    return load_json(root / RELATIVE, {})


def validate(policy: dict) -> dict:
    checks = {
        "stage": policy.get("stage") == "V330.64",
        "qualification_flag_boolean": isinstance(policy.get("qualification_enabled"), bool),
        "paper_endpoint_only": policy.get("paper_base_url") == "https://paper-api.alpaca.markets",
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
        "live_network_disabled": policy.get("live_network_enabled") is False,
        "zero_new_orders": int(policy.get("maximum_new_orders_per_day", -1)) == 0,
        "positive_poll_interval": int(policy.get("cycle_interval_seconds", 0)) >= 15,
        "valid_success_ratio": 0 < float(policy.get("minimum_success_ratio", 0)) <= 1,
        "positive_targets": int(policy.get("minimum_successful_cycles", 0)) > 0
        and float(policy.get("minimum_observation_minutes", 0)) > 0,
    }
    return {"valid": all(checks.values()), "checks": checks, "failed": [k for k, v in checks.items() if not v]}
