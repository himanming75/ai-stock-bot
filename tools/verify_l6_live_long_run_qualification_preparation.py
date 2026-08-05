from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = (
    ROOT / "release/l6_live_long_run_qualification_preparation/actual"
)
result = json.loads(
    (actual / "l6_offline_qualification.json").read_text(
        encoding="utf-8-sig"
    )
)
certificate = json.loads(
    (actual / "l6_preparation_certificate.json").read_text(
        encoding="utf-8-sig"
    )
)

checks = {
    "stage": result.get("stage") == "L6",
    "status": result.get("status") == "PASS",
    "qualified": result.get("qualified") is True,
    "prepared_state": (
        result.get("state") == "LIVE_LONG_RUN_PREPARATION_QUALIFIED"
    ),
    "three_cycles": result.get("successful_cycles") == 3,
    "zero_failures": result.get("failed_cycles") == 0,
    "actual_long_run_blocked": (
        result.get("actual_live_long_run_allowed") is False
    ),
    "actual_not_qualified": (
        result.get("actual_live_long_run_qualified") is False
    ),
    "live_not_complete": result.get("live_complete") is False,
    "production_release_blocked": (
        result.get("production_release_allowed") is False
    ),
    "auto_replay_off": (
        result.get("automatic_order_replay_enabled") is False
    ),
    "auto_restart_off": (
        result.get("automatic_broker_restart_enabled") is False
    ),
    "live_network_off": result.get("live_network_enabled") is False,
    "live_write_off": result.get("live_write_enabled") is False,
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
    "certificate_offline_only": (
        certificate.get("offline_preparation_qualified") is True
        and certificate.get("actual_live_long_run_qualified") is False
    ),
}
verification = {
    "verification_stage": "L6_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
