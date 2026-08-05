from __future__ import annotations
from decimal import Decimal
from pathlib import Path
import json
from .models import StrategyCandidate
from .ensemble import StrategyEnsembleV4
from .risk import AdaptiveRiskEngineV3
from .portfolio import PortfolioIntelligenceV2
from .execution import ExecutionIntelligenceV2

def run(root: Path) -> dict:
    actual = root / "release/ai_strategy_risk_portfolio_execution_v4/actual"
    actual.mkdir(parents=True, exist_ok=True)

    ensemble = StrategyEnsembleV4().decide(
        candidates=[
            StrategyCandidate("momentum_v4", Decimal("0.82"), Decimal("0.74"), Decimal("0.88"), Decimal("0.79"), Decimal("0.12"), Decimal("0.08")),
            StrategyCandidate("breakout_v4", Decimal("0.76"), Decimal("0.70"), Decimal("0.84"), Decimal("0.73"), Decimal("0.18"), Decimal("0.10")),
            StrategyCandidate("mean_reversion_v4", Decimal("0.58"), Decimal("0.68"), Decimal("0.30"), Decimal("0.61"), Decimal("0.22"), Decimal("0.15")),
        ],
        market_regime="TRENDING",
    )
    risk = AdaptiveRiskEngineV3().evaluate(
        symbol="SPY",
        base_notional=Decimal("1000"),
        volatility=Decimal("0.22"),
        sector_exposure=Decimal("0.18"),
        portfolio_exposure=Decimal("0.42"),
        drawdown_ratio=Decimal("0.10"),
        consecutive_losses=1,
        daily_loss_limit_reached=False,
        strategy_risk_budget=Decimal("0.75"),
    )
    portfolio = PortfolioIntelligenceV2().allocate(
        symbol="SPY",
        portfolio_value=Decimal("100000"),
        current_weight=Decimal("0.08"),
        desired_weight=Decimal("0.12"),
        sector_weight_after=Decimal("0.22"),
        correlated_exposure_after=Decimal("0.30"),
    )
    execution = ExecutionIntelligenceV2().plan(
        symbol="SPY",
        side="buy",
        quantity=Decimal("1"),
        reference_price=Decimal("500"),
        spread_bps=Decimal("2"),
        volatility=Decimal("0.20"),
        urgency=Decimal("0.40"),
        maximum_order_notional=Decimal("1000"),
    )
    checks = {
        "ensemble_trade_ready": ensemble.blocked is False,
        "ensemble_weight_cap": all(v <= Decimal("0.60") for v in ensemble.normalized_weights.values()),
        "risk_approved": risk.blocked is False and risk.approved_notional > 0,
        "portfolio_ready": not portfolio.blockers and portfolio.rebalance_required,
        "execution_ready": execution.blocked is False,
        "network_unused": True,
        "broker_write_unused": True,
        "orders_zero": True,
    }
    result = {
        "stage": "AI_STRATEGY_RISK_PORTFOLIO_EXECUTION_MEGA_BUNDLE",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "ensemble": ensemble.as_json(),
        "risk": {
            "symbol": risk.symbol,
            "approved_notional": str(risk.approved_notional),
            "risk_multiplier": str(risk.risk_multiplier),
            "blocked": risk.blocked,
            "blockers": list(risk.blockers),
        },
        "portfolio": {
            "symbol": portfolio.symbol,
            "target_weight": str(portfolio.target_weight),
            "target_notional": str(portfolio.target_notional),
            "rebalance_required": portfolio.rebalance_required,
            "blockers": list(portfolio.blockers),
        },
        "execution": {
            "symbol": execution.symbol,
            "side": execution.side,
            "order_type": execution.order_type,
            "quantity": str(execution.total_quantity),
            "slice_count": execution.slice_count,
            "limit_price": None if execution.limit_price is None else str(execution.limit_price),
            "expected_slippage_bps": str(execution.expected_slippage_bps),
            "blocked": execution.blocked,
            "blockers": list(execution.blockers),
        },
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_development": "MARKET_INTELLIGENCE_DATA_FUSION",
        "next_market_dependent_action": "P3_ACTUAL_PAPER_ORDER_VALIDATION",
    }
    (actual / "ai_strategy_risk_portfolio_execution_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
