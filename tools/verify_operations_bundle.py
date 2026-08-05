from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
monitor = json.loads(
    (
        ROOT
        / "release/operations_bundle/actual/"
          "monitor_result.json"
    ).read_text(encoding="utf-8-sig")
)
l1 = json.loads(
    (
        ROOT
        / "release/operations_bundle/actual/"
          "l1_safety_preparation_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "monitor_ok": monitor.get("severity") == "OK",
    "l1_preparation_pass": l1.get("status") == "PASS",
    "live_activation_blocked": (
        l1.get("live_activation_allowed") is False
    ),
    "live_network_off": (
        l1.get("live_network_enabled") is False
    ),
    "live_write_off": (
        l1.get("live_write_enabled") is False
    ),
    "live_orders_zero": (
        l1.get("actual_live_orders_submitted") == 0
    ),
}
result = {
    "verification_stage": "OPERATIONS_BUNDLE",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [key for key, passed in checks.items() if not passed],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
