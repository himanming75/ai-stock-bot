from __future__ import annotations
from decimal import Decimal

from .models import BrainDecision, StrategyCandidate
from .scoring import rank_candidates


D = Decimal


class AutonomousAIBrain:
    def decide(
        self,
        *,
        market_regime: str,
        candidates: list[StrategyCandidate],
        system_health: str,
        market_open: bool,
        drawdown_guard_active: bool,
        promotion_threshold: Decimal = D("0.70"),
    ) -> tuple[BrainDecision, list[dict]]:
        if system_health.upper() == "CRITICAL":
            return (
                BrainDecision(
                    action="ALL_STOP",
                    selected_strategy_id=None,
                    confidence=D("0"),
                    autonomous_state="FAILSAFE_BLOCKED",
                    reason="CRITICAL_SYSTEM_HEALTH",
                    promotion_recommended=False,
                    automatic_promotion_performed=False,
                    order_submission_allowed=False,
                ),
                [],
            )

        if drawdown_guard_active:
            return (
                BrainDecision(
                    action="WAIT",
                    selected_strategy_id=None,
                    confidence=D("0"),
                    autonomous_state="RISK_HOLD",
                    reason="DRAWDOWN_GUARD_ACTIVE",
                    promotion_recommended=False,
                    automatic_promotion_performed=False,
                    order_submission_allowed=False,
                ),
                [],
            )

        if not market_open:
            return (
                BrainDecision(
                    action="WAIT",
                    selected_strategy_id=None,
                    confidence=D("0"),
                    autonomous_state="MARKET_CLOSED",
                    reason="MARKET_NOT_OPEN",
                    promotion_recommended=False,
                    automatic_promotion_performed=False,
                    order_submission_allowed=False,
                ),
                [],
            )

        ranked = rank_candidates(candidates)
        eligible = [
            item for item in ranked
            if item.eligible
        ]
        if not eligible:
            return (
                BrainDecision(
                    action="WAIT",
                    selected_strategy_id=None,
                    confidence=D("0"),
                    autonomous_state="ABSTAIN",
                    reason="NO_ELIGIBLE_STRATEGY",
                    promotion_recommended=False,
                    automatic_promotion_performed=False,
                    order_submission_allowed=False,
                ),
                [item.to_dict() for item in ranked],
            )

        winner = eligible[0]
        candidate = next(
            item for item in candidates
            if item.strategy_id == winner.strategy_id
        )

        action = candidate.signal.upper()
        if action not in {"BUY", "SELL", "WAIT"}:
            action = "WAIT"

        confidence = max(
            D("0"),
            min(D("1"), candidate.confidence),
        )
        promotion_recommended = (
            winner.total_score >= promotion_threshold
            and action != "WAIT"
        )

        return (
            BrainDecision(
                action=action,
                selected_strategy_id=winner.strategy_id,
                confidence=confidence,
                autonomous_state=(
                    "DECISION_READY"
                    if action != "WAIT"
                    else "ABSTAIN"
                ),
                reason=(
                    f"BEST_REGIME_FIT:{market_regime.upper()}"
                ),
                promotion_recommended=promotion_recommended,
                automatic_promotion_performed=False,
                order_submission_allowed=False,
            ),
            [item.to_dict() for item in ranked],
        )
