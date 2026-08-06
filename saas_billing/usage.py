from __future__ import annotations
from collections import defaultdict

from .plans import get_plan


class UsageMeter:
    def __init__(self) -> None:
        self.values = defaultdict(float)

    def record(
        self,
        *,
        user_id: str,
        metric: str,
        quantity: float = 1.0,
    ) -> None:
        if quantity < 0:
            raise ValueError("NEGATIVE_USAGE_NOT_ALLOWED")
        self.values[(user_id, metric)] += quantity

    def get(
        self,
        *,
        user_id: str,
        metric: str,
    ) -> float:
        return self.values[(user_id, metric)]

    def evaluate_limit(
        self,
        *,
        user_id: str,
        plan: str,
        metric: str,
    ) -> dict:
        plan_data = get_plan(plan)
        mapping = {
            "workspace_count": "workspace_limit",
            "broker_count": "broker_limit",
            "ai_requests": "ai_requests_per_day",
            "backtests": "backtests_per_month",
            "paper_runtime_hours": (
                "paper_runtime_hours_per_month"
            ),
        }
        if metric not in mapping:
            raise ValueError("UNKNOWN_USAGE_METRIC")
        limit = float(plan_data[mapping[metric]])
        used = float(self.get(
            user_id=user_id,
            metric=metric,
        ))
        return {
            "metric": metric,
            "used": used,
            "limit": limit,
            "remaining": max(limit - used, 0),
            "allowed": used <= limit,
        }
