from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


class SchedulerPreview:
    def plan(
        self,
        *,
        task_count: int,
        worker_count: int,
        interval_seconds: int,
    ) -> dict[str, Any]:
        if interval_seconds <= 0:
            raise ValueError("POSITIVE_INTERVAL_REQUIRED")
        estimated_cycles = (
            (task_count + worker_count - 1) // worker_count
            if worker_count > 0 else 0
        )
        return {
            "task_count": task_count,
            "worker_count": worker_count,
            "interval_seconds": interval_seconds,
            "estimated_cycles": estimated_cycles,
            "scheduler_state": "PREVIEW_ONLY",
            "automatic_scheduler_started": False,
            "actual_parallel_runtime_started": False,
        }


class RuntimeHealthMonitor:
    def evaluate(
        self,
        *,
        worker_results: list[dict[str, Any]],
        load_balance: dict[str, Any],
    ) -> dict[str, Any]:
        completed = sum(
            1 for row in worker_results
            if row.get("scan_state") == "COMPLETED_OFFLINE"
        )
        failures = len(worker_results) - completed
        checks = {
            "all_tasks_completed": failures == 0,
            "balanced": load_balance.get("balanced") is True,
            "network_unused": all(
                row.get("market_data_network_used") is False
                and row.get("broker_network_used") is False
                for row in worker_results
            ),
            "orders_zero": all(
                row.get("order_created") is False
                for row in worker_results
            ),
        }
        return {
            "stage": "DISTRIBUTED_RUNTIME_HEALTH",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "failed": [key for key, value in checks.items() if not value],
            "status": "PASS" if all(checks.values()) else "FAIL",
            "completed_tasks": completed,
            "failed_tasks": failures,
            "automatic_recovery_performed": False,
        }


class RecoveryQueuePreview:
    def build(
        self,
        *,
        failed_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        entries = [
            {
                "task_id": row.get("task_id"),
                "symbol": row.get("symbol"),
                "reason": row.get("failure_reason", "UNKNOWN"),
                "retry_allowed": False,
            }
            for row in failed_results
        ]
        return {
            "entry_count": len(entries),
            "entries": entries,
            "automatic_retry_enabled": False,
            "automatic_recovery_enabled": False,
            "actual_retry_performed": False,
        }
