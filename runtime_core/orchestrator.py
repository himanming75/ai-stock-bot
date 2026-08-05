from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any
import uuid

from .allocation import CapitalAllocationEngine
from .models import OrderCandidate
from .plugins import StrategyRegistry
from .portfolio import PortfolioExposureManager
from .risk import RuntimeRiskEvaluator


class RuntimeOrchestrator:
    def __init__(
        self,
        *,
        registry: StrategyRegistry,
        risk: RuntimeRiskEvaluator | None = None,
        allocation: CapitalAllocationEngine | None = None,
        portfolio: PortfolioExposureManager | None = None,
    ) -> None:
        self.registry = registry
        self.risk = risk or RuntimeRiskEvaluator()
        self.allocation = allocation or CapitalAllocationEngine()
        self.portfolio = portfolio or PortfolioExposureManager()

    @staticmethod
    def _candidate_id(value: dict[str, Any]) -> str:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return "r10-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def run_cycle(
        self,
        *,
        session_snapshot: dict[str, Any],
        strategy_id: str,
        market_snapshot: dict[str, Any],
        portfolio_snapshot: dict[str, Any],
        daily_state: dict[str, Any],
        cycle_number: int,
    ) -> dict[str, Any]:
        runtime = session_snapshot["runtime_snapshot"]
        plugin = self.registry.get(strategy_id)
        if runtime["horizon"] not in plugin.supported_horizons:
            raise ValueError("STRATEGY_HORIZON_NOT_SUPPORTED")

        signals = plugin.generate_signals(
            market_snapshot=market_snapshot,
            runtime_snapshot=runtime,
        )
        signal_results = []
        candidates = []

        for signal in signals:
            risk_result = self.risk.evaluate(
                signal=signal,
                runtime_snapshot=runtime,
                daily_state=daily_state,
            )
            allocation = self.allocation.allocate(
                signal=signal,
                runtime_snapshot=runtime,
                portfolio_snapshot=portfolio_snapshot,
            )

            candidate = None
            portfolio_validation = None
            portfolio_preview = None
            if risk_result["approved"] and not allocation.blocked:
                raw = {
                    "session_id": session_snapshot["session_id"],
                    "cycle_number": cycle_number,
                    "strategy_id": signal.strategy_id,
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "notional": str(allocation.approved_notional),
                }
                candidate = OrderCandidate(
                    candidate_id=self._candidate_id(raw),
                    strategy_id=signal.strategy_id,
                    symbol=signal.symbol,
                    side=signal.side,
                    order_type=runtime["allowed_order_types"][0],
                    time_in_force=runtime["time_in_force"],
                    notional=allocation.approved_notional,
                    reference_price=signal.reference_price,
                    broker_mode=runtime["broker_mode"],
                    submit_allowed=False,
                )
                portfolio_validation = self.portfolio.validate_candidate(
                    candidate=candidate,
                    runtime_snapshot=runtime,
                    portfolio_snapshot=portfolio_snapshot,
                )
                if portfolio_validation["valid"]:
                    portfolio_preview = self.portfolio.preview_apply(
                        candidate=candidate,
                        portfolio_snapshot=portfolio_snapshot,
                    )
                    candidates.append(candidate.as_json())

            signal_results.append({
                "signal": {
                    "strategy_id": signal.strategy_id,
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "strength": str(signal.strength),
                    "reference_price": str(signal.reference_price),
                    "reason": signal.reason,
                },
                "risk": risk_result,
                "allocation": allocation.as_json(),
                "order_candidate": (
                    candidate.as_json() if candidate else None
                ),
                "portfolio_validation": portfolio_validation,
                "portfolio_preview": portfolio_preview,
            })

        return {
            "stage": "BUNDLE_A_R7_TO_R10",
            "cycle_id": f"cycle-{uuid.uuid4().hex}",
            "cycle_number": cycle_number,
            "session_id": session_snapshot["session_id"],
            "profile_name": runtime["profile_name"],
            "horizon": runtime["horizon"],
            "strategy_id": strategy_id,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "signal_count": len(signals),
            "order_candidate_count": len(candidates),
            "signals": signal_results,
            "order_candidates": candidates,
            "strategy_execution_preview_only": True,
            "actual_strategy_execution_enabled": False,
            "broker_network_enabled": False,
            "broker_write_enabled": False,
            "automatic_order_submission_enabled": False,
            "actual_portfolio_modified": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "status": "PASS",
        }
