from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .metrics import MetricsCollector
from .queueing import SymbolQueue, SymbolTask
from .scheduler import (
    RecoveryQueuePreview,
    RuntimeHealthMonitor,
    SchedulerPreview,
)
from .workers import LoadBalancer, WorkerPool


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run(root: Path) -> dict[str, Any]:
    actual = root / "release/ai_monitoring_distributed_runtime/actual"
    actual.mkdir(parents=True, exist_ok=True)

    shadow = read_json(
        root / "release/shadow_trading_production_approval/actual/"
               "shadow_trading_production_approval_result.json"
    )
    feature = read_json(
        root / "release/feature_engine_auto_optimization/actual/"
               "feature_engine_auto_optimization_result.json"
    )
    validation = read_json(
        root / "release/validation_support_mega_bundle/actual/"
               "validation_support_result.json"
    )

    metrics = MetricsCollector().collect(
        shadow_result=shadow,
        feature_result=feature,
        validation_result=validation,
    )

    queue = SymbolQueue()
    symbols = [
        ("task-1", "AAPL", 5, "momentum_v3"),
        ("task-2", "MSFT", 4, "swing_v1"),
        ("task-3", "SPY", 5, "breakout_v3"),
        ("task-4", "XLV", 2, "mean_reversion_v3"),
        ("task-5", "NVDA", 4, "momentum_v3"),
        ("task-6", "AMD", 3, "scalping_v1"),
        ("task-7", "META", 3, "swing_v1"),
        ("task-8", "GOOGL", 2, "breakout_v3"),
    ]
    for task_id, symbol, priority, strategy_id in symbols:
        queue.put(SymbolTask(
            task_id=task_id,
            symbol=symbol,
            priority=priority,
            strategy_id=strategy_id,
        ))

    queue_before = queue.snapshot()
    worker_count = 3
    results = WorkerPool(worker_count).drain(queue)
    load_balance = LoadBalancer().summarize(
        results=results,
        worker_count=worker_count,
    )
    scheduler = SchedulerPreview().plan(
        task_count=len(results),
        worker_count=worker_count,
        interval_seconds=60,
    )
    health = RuntimeHealthMonitor().evaluate(
        worker_results=results,
        load_balance=load_balance,
    )
    recovery = RecoveryQueuePreview().build(
        failed_results=[
            row for row in results
            if row.get("scan_state") != "COMPLETED_OFFLINE"
        ]
    )

    alert_feed = []
    if metrics["health_status"] != "PASS":
        alert_feed.append({
            "severity": "ERROR",
            "subject": "Monitoring health failure",
        })
    if metrics["release_gate"] != "LOCKED":
        alert_feed.append({
            "severity": "CRITICAL",
            "subject": "Release gate unexpectedly unlocked",
        })
    if not load_balance["balanced"]:
        alert_feed.append({
            "severity": "WARNING",
            "subject": "Worker imbalance detected",
        })

    checks = {
        "shadow_framework_pass": shadow.get("status") == "PASS",
        "feature_framework_pass": feature.get("status") == "PASS",
        "validation_framework_pass": validation.get("status") == "PASS",
        "metrics_pass": metrics["health_status"] == "PASS",
        "eight_tasks_queued": len(queue_before) == 8,
        "eight_tasks_processed": len(results) == 8,
        "three_workers_used": len(load_balance["worker_counts"]) == 3,
        "load_balanced": load_balance["balanced"] is True,
        "runtime_health_pass": health["status"] == "PASS",
        "scheduler_preview_only": (
            scheduler["automatic_scheduler_started"] is False
        ),
        "recovery_empty": recovery["entry_count"] == 0,
        "alert_feed_empty": not alert_feed,
        "orders_zero": all(
            row["order_created"] is False for row in results
        ),
    }

    result = {
        "stage": "AI_MONITORING_DISTRIBUTED_RUNTIME_MEGA_BUNDLE",
        "state": "OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "ai_health_dashboard": "READY",
        "risk_dashboard": "READY",
        "strategy_dashboard": "READY",
        "shadow_portfolio_dashboard": "READY",
        "metrics_collector": "READY",
        "summary_feed": "READY",
        "alert_feed": "READY",
        "symbol_queue": "READY",
        "worker_pool": "READY",
        "parallel_scanner": "READY_OFFLINE",
        "load_balancer": "READY",
        "scheduler": "READY_PREVIEW_ONLY",
        "runtime_metrics": "READY",
        "health_monitor": "READY",
        "recovery_queue": "READY_PREVIEW_ONLY",
        "dashboard_read_only": True,
        "metrics": metrics,
        "queue_snapshot_before_processing": queue_before,
        "worker_results": results,
        "load_balance": load_balance,
        "scheduler_preview": scheduler,
        "runtime_health": health,
        "recovery_queue_preview": recovery,
        "alert_feed_entries": alert_feed,
        "actual_parallel_runtime_started": False,
        "actual_scheduler_started": False,
        "automatic_recovery_enabled": False,
        "automatic_recovery_performed": False,
        "actual_external_network_used": False,
        "actual_market_data_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_action": "P2_ACTUAL_PAPER_BROKER_READ_VALIDATION",
    }
    (actual / "ai_monitoring_distributed_runtime_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
