from __future__ import annotations
from collections import defaultdict
from decimal import Decimal

from .models import AllocationDecision, PortfolioCandidate
from .risk import dynamic_cash_floor, loss_budget_state, risk_multiplier


D = Decimal


class AutonomousPortfolioAllocator:
    def allocate(
        self,
        *,
        candidates: list[PortfolioCandidate],
        regime: str,
        portfolio_volatility: Decimal,
        drawdown_ratio: Decimal,
        daily_loss_ratio: Decimal,
        weekly_loss_ratio: Decimal,
        max_position_weight: Decimal = D("0.15"),
        max_sector_weight: Decimal = D("0.30"),
        max_correlation_group_weight: Decimal = D("0.25"),
        rebalance_threshold: Decimal = D("0.02"),
        daily_loss_limit: Decimal = D("0.03"),
        weekly_loss_limit: Decimal = D("0.06"),
    ) -> dict:
        risk_state = loss_budget_state(
            daily_loss_ratio=daily_loss_ratio,
            weekly_loss_ratio=weekly_loss_ratio,
            daily_limit=daily_loss_limit,
            weekly_limit=weekly_loss_limit,
        )

        cash_floor = dynamic_cash_floor(
            regime=regime,
            portfolio_volatility=portfolio_volatility,
            drawdown_ratio=drawdown_ratio,
        )
        allocatable = D("1") - cash_floor

        if not risk_state["new_entries_allowed"]:
            decisions = [
                AllocationDecision(
                    symbol=item.symbol,
                    target_weight=item.current_weight,
                    current_weight=item.current_weight,
                    delta_weight=D("0"),
                    action="HOLD",
                    reason="LOSS_BUDGET_GUARD_ACTIVE",
                    constrained_by=("RISK_HOLD",),
                )
                for item in candidates
            ]
            return {
                "cash_target": str(cash_floor),
                "allocatable_weight": str(allocatable),
                "risk_state": risk_state,
                "allocations": [
                    item.to_dict() for item in decisions
                ],
                "rebalance_required": False,
            }

        eligible = [
            item for item in candidates
            if item.action.upper() == "BUY"
            and item.confidence > 0
        ]

        raw_scores = {}
        for item in eligible:
            multiplier = risk_multiplier(
                confidence=item.confidence,
                volatility=item.volatility,
                drawdown_ratio=drawdown_ratio,
            )
            raw_scores[item.symbol] = (
                max(D("0"), item.expected_return)
                * multiplier
            )

        total_score = sum(raw_scores.values(), D("0"))
        sector_usage = defaultdict(lambda: D("0"))
        correlation_usage = defaultdict(lambda: D("0"))
        decisions = []

        for item in candidates:
            constraints = []

            if item.symbol not in raw_scores or total_score <= 0:
                target = D("0")
                reason = "NOT_ELIGIBLE_FOR_NEW_ALLOCATION"
            else:
                target = (
                    raw_scores[item.symbol]
                    / total_score
                    * allocatable
                )

                if target > max_position_weight:
                    target = max_position_weight
                    constraints.append("MAX_POSITION_WEIGHT")

                sector_remaining = max(
                    D("0"),
                    max_sector_weight
                    - sector_usage[item.sector],
                )
                if target > sector_remaining:
                    target = sector_remaining
                    constraints.append("MAX_SECTOR_WEIGHT")

                group_remaining = max(
                    D("0"),
                    max_correlation_group_weight
                    - correlation_usage[
                        item.correlation_group
                    ],
                )
                if target > group_remaining:
                    target = group_remaining
                    constraints.append(
                        "MAX_CORRELATION_GROUP_WEIGHT"
                    )

                sector_usage[item.sector] += target
                correlation_usage[
                    item.correlation_group
                ] += target
                reason = "RISK_ADJUSTED_ALLOCATION"

            delta = target - item.current_weight
            if abs(delta) < rebalance_threshold:
                action = "HOLD"
                delta = D("0")
            elif delta > 0:
                action = "INCREASE"
            else:
                action = "DECREASE"

            decisions.append(
                AllocationDecision(
                    symbol=item.symbol,
                    target_weight=target,
                    current_weight=item.current_weight,
                    delta_weight=delta,
                    action=action,
                    reason=reason,
                    constrained_by=tuple(constraints),
                )
            )

        invested = sum(
            (
                D(item.to_dict()["target_weight"])
                for item in decisions
            ),
            D("0"),
        )
        effective_cash = max(
            cash_floor,
            D("1") - invested,
        )

        return {
            "cash_target": str(effective_cash),
            "allocatable_weight": str(
                D("1") - effective_cash
            ),
            "risk_state": risk_state,
            "allocations": [
                item.to_dict() for item in decisions
            ],
            "sector_usage": {
                key: str(value)
                for key, value in sector_usage.items()
            },
            "correlation_group_usage": {
                key: str(value)
                for key, value in correlation_usage.items()
            },
            "rebalance_required": any(
                item.action in {"INCREASE", "DECREASE"}
                for item in decisions
            ),
        }
