from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
catalog = json.loads(
    (
        ROOT / "release/r4_configuration_profiles/actual/"
               "profile_catalog.json"
    ).read_text(encoding="utf-8-sig")
)

profiles = catalog.get("profiles", [])
checks = {
    "stage": catalog.get("stage") == "R4_PROFILE_CATALOG",
    "profile_count": len(profiles) == 5,
    "all_profiles_valid": catalog.get("all_profiles_valid") is True,
    "all_horizons_present": (
        {"ultra_short", "day", "swing", "position"}
        <= {item.get("horizon") for item in profiles}
    ),
    "paper_live_profiles_present": (
        {"paper", "live"}
        <= {item.get("broker_mode") for item in profiles}
    ),
    "allocation_preserved": all(
        item.get("allocation_enabled") is True
        for item in profiles
    ),
    "multi_account_field_preserved": all(
        isinstance(item.get("multi_account_enabled"), bool)
        for item in profiles
    ),
    "actual_activation_not_performed": (
        catalog.get("actual_activation_performed") is False
    ),
    "network_unused": catalog.get("broker_network_used") is False,
    "paper_orders_zero": (
        catalog.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        catalog.get("actual_live_orders_submitted") == 0
    ),
}
result = {
    "verification_stage": "R4_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
