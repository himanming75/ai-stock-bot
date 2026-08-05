from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/l1_live_safety_boundary/actual/l1_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "L1",
    "status": result.get("status") == "PASS",
    "live_kill_switch_active": (
        result.get("live_kill_switch", {}).get(
            "live_kill_switch_active"
        ) is True
    ),
    "live_read_only_blocked": (
        result.get("live_read_only_allowed") is False
    ),
    "live_activation_blocked": (
        result.get("live_activation_allowed") is False
    ),
    "live_network_off": (
        result.get("live_network_enabled") is False
    ),
    "live_write_off": result.get("live_write_enabled") is False,
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
}
verification = {
    "verification_stage": "L1",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
