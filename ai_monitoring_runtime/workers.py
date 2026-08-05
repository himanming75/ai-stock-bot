from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .queueing import SymbolQueue, SymbolTask


class Worker:
    def __init__(self, worker_id: str) -> None:
        self.worker_id = worker_id

    def process(self, task: SymbolTask) -> dict[str, Any]:
        score_seed = sum(ord(char) for char in task.symbol) % 100
        score = score_seed / 100
        return {
            "worker_id": self.worker_id,
            "task_id": task.task_id,
            "symbol": task.symbol,
            "strategy_id": task.strategy_id,
            "scan_score": f"{score:.4f}",
            "scan_state": "COMPLETED_OFFLINE",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "market_data_network_used": False,
            "broker_network_used": False,
            "order_created": False,
        }


class WorkerPool:
    def __init__(self, worker_count: int) -> None:
        if worker_count <= 0:
            raise ValueError("POSITIVE_WORKER_COUNT_REQUIRED")
        self.workers = [
            Worker(f"worker-{index + 1}")
            for index in range(worker_count)
        ]

    def drain(self, queue: SymbolQueue) -> list[dict[str, Any]]:
        results = []
        index = 0
        while queue.size() > 0:
            worker = self.workers[index % len(self.workers)]
            results.append(worker.process(queue.get()))
            index += 1
        return results


class LoadBalancer:
    def summarize(
        self,
        *,
        results: list[dict[str, Any]],
        worker_count: int,
    ) -> dict[str, Any]:
        counts = {
            f"worker-{index + 1}": 0
            for index in range(worker_count)
        }
        for row in results:
            counts[row["worker_id"]] += 1

        values = list(counts.values())
        imbalance = max(values) - min(values) if values else 0
        return {
            "worker_counts": counts,
            "task_count": len(results),
            "worker_count": worker_count,
            "maximum_task_imbalance": imbalance,
            "balanced": imbalance <= 1,
        }
