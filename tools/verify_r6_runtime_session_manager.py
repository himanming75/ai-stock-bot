from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/r6_runtime_session_manager/actual/"
               "last_session_preview.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "R6",
    "completed": result.get("state") == "PREVIEW_SESSION_COMPLETE",
    "profile_snapshot": bool(result.get("runtime_snapshot")),
    "snapshot_hash": len(result.get("runtime_snapshot_hash", "")) == 64,
    "policy_valid": result.get("policy", {}).get("valid") is True,
    "network_off": result.get("broker_network_enabled") is False,
    "write_off": result.get("broker_write_enabled") is False,
    "automatic_submission_off": (
        result.get("automatic_order_submission_enabled") is False
    ),
    "automatic_replay_off": (
        result.get("automatic_order_replay_enabled") is False
    ),
    "automatic_restart_off": (
        result.get("automatic_broker_restart_enabled") is False
    ),
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "lock_released": not (
        ROOT / "release/r6_runtime_session_manager/actual/session.lock.json"
    ).exists(),
}
verification = {
    "verification_stage": "R6_PREPARATION",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
