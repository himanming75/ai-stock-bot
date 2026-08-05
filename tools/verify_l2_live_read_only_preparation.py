from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/l2_live_read_only_preparation/actual/"
               "l2_offline_qualification.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "L2",
    "status": result.get("status") == "PASS",
    "fixture_mode": result.get("mode") == (
        "OFFLINE_FIXTURE_LIVE_READ_ONLY_PREPARATION"
    ),
    "config_valid": result.get("config", {}).get("valid") is True,
    "actual_live_read_blocked": (
        result.get("actual_live_read_allowed") is False
    ),
    "live_network_off": result.get("live_network_enabled") is False,
    "live_write_off": result.get("live_write_enabled") is False,
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
    "snapshot_hash": len(result.get("snapshot_hash", "")) == 64,
}
verification = {
    "verification_stage": "L2_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
