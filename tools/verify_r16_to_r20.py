from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/r16_to_r20_realtime_paper_ops/actual/"
               "r16_to_r20_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": (
        result.get("stage") ==
        "R16_TO_R20_REALTIME_PAPER_OPERATIONS_PREPARATION"
    ),
    "status": result.get("status") == "PASS",
    "qualified_state": (
        result.get("state") ==
        "REALTIME_PAPER_OPERATIONS_OFFLINE_QUALIFIED"
    ),
    "r16_ready": (
        result.get("r16_paper_session_coordinator") == "READY"
    ),
    "r17_ready": result.get("r17_market_clock_scheduler") == "READY",
    "r18_ready": (
        result.get("r18_account_position_sync_preview") == "READY"
    ),
    "r19_ready": result.get("r19_safe_order_queue") == "READY",
    "r20_ready": (
        result.get("r20_order_lifecycle_monitor") == "READY"
    ),
    "paper_session_not_started": (
        result.get("actual_paper_session_started") is False
    ),
    "market_api_unused": (
        result.get("actual_market_api_used") is False
    ),
    "broker_read_not_performed": (
        result.get("actual_broker_read_performed") is False
    ),
    "broker_network_unused": (
        result.get("actual_broker_network_used") is False
    ),
    "broker_write_unused": (
        result.get("actual_broker_write_used") is False
    ),
    "dispatch_not_performed": (
        result.get("actual_order_dispatch_performed") is False
    ),
    "runtime_start_off": (
        result.get("automatic_runtime_start_enabled") is False
    ),
    "submission_off": (
        result.get("automatic_order_submission_enabled") is False
    ),
    "replay_off": (
        result.get("automatic_order_replay_enabled") is False
    ),
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
}
verification = {
    "verification_stage": "R16_TO_R20",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
