from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/ai_monitoring_distributed_runtime/actual/"
               "ai_monitoring_distributed_runtime_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": (
        result.get("stage")
        == "AI_MONITORING_DISTRIBUTED_RUNTIME_MEGA_BUNDLE"
    ),
    "status": result.get("status") == "PASS",
    "dashboard_ready": result.get("ai_health_dashboard") == "READY",
    "metrics_ready": result.get("metrics_collector") == "READY",
    "queue_ready": result.get("symbol_queue") == "READY",
    "workers_ready": result.get("worker_pool") == "READY",
    "scanner_ready": result.get("parallel_scanner") == "READY_OFFLINE",
    "load_balancer_ready": result.get("load_balancer") == "READY",
    "scheduler_preview_only": result.get("scheduler") == "READY_PREVIEW_ONLY",
    "health_ready": result.get("health_monitor") == "READY",
    "recovery_preview_only": (
        result.get("recovery_queue") == "READY_PREVIEW_ONLY"
    ),
    "dashboard_read_only": result.get("dashboard_read_only") is True,
    "runtime_not_started": (
        result.get("actual_parallel_runtime_started") is False
    ),
    "scheduler_not_started": (
        result.get("actual_scheduler_started") is False
    ),
    "recovery_off": (
        result.get("automatic_recovery_enabled") is False
    ),
    "network_unused": result.get("actual_external_network_used") is False,
    "market_network_unused": (
        result.get("actual_market_data_network_used") is False
    ),
    "broker_read_unused": (
        result.get("actual_broker_read_performed") is False
    ),
    "broker_write_unused": (
        result.get("actual_broker_write_performed") is False
    ),
    "orders_not_submitted": (
        result.get("actual_order_submission_performed") is False
    ),
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "AI_MONITORING_DISTRIBUTED_RUNTIME",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
