from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class RequestMetric:
    route: str
    latency_ms: float
    status_code: int


class MetricsRegistry:
    def __init__(self, max_samples: int = 5000) -> None:
        self.samples = deque(maxlen=max_samples)
        self.counters = {
            "requests_total": 0,
            "errors_total": 0,
            "notifications_created": 0,
            "notifications_failed": 0,
            "backup_success": 0,
            "backup_failure": 0,
        }

    def record_request(
        self,
        *,
        route: str,
        latency_ms: float,
        status_code: int,
    ) -> None:
        self.samples.append(
            RequestMetric(
                route=route,
                latency_ms=latency_ms,
                status_code=status_code,
            )
        )
        self.counters["requests_total"] += 1
        if status_code >= 400:
            self.counters["errors_total"] += 1

    def increment(self, name: str) -> None:
        self.counters[name] = (
            self.counters.get(name, 0) + 1
        )

    def snapshot(self) -> dict:
        latencies = [
            item.latency_ms
            for item in self.samples
        ]
        requests = self.counters[
            "requests_total"
        ]
        errors = self.counters[
            "errors_total"
        ]
        ordered = sorted(latencies)

        def percentile(value: float) -> float:
            if not ordered:
                return 0.0
            index = int(
                round((len(ordered) - 1) * value)
            )
            return float(ordered[index])

        return {
            **self.counters,
            "error_rate": (
                errors / requests
                if requests else 0.0
            ),
            "average_latency_ms": (
                mean(latencies)
                if latencies else 0.0
            ),
            "p50_latency_ms": percentile(0.50),
            "p95_latency_ms": percentile(0.95),
            "p99_latency_ms": percentile(0.99),
            "sample_count": len(self.samples),
        }
