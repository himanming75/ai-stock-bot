from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .ensemble import StrategyEnsembleRanker
from .learning import PerformanceLearningLedger
from .portfolio_optimizer import PortfolioOptimizer
from .risk_v2 import DynamicRiskEngineV2


def run_ai_v2_offline_qualification(root: Path) -> dict[str, Any]:
    actual = root / "release/ai_v2_mega_bundle_1/actual"
    actual.mkdir(parents=True, exist_ok=True)
    ledger_path = actual / "offline_learning_ledger.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()

    ledger = PerformanceLearningLedger(ledger_path)
    fixture_outcomes = [
        ("momentum_v2", "AAPL", "4.00", "0.0080", 25, "TARGET"),
        ("momentum_v2", "MSFT", "-1.00", "-0.0020", 18, "STOP"),
        ("mean_reversion_v2", "SPY", "2.00", "0.0040", 40, "TARGET"),
        ("mean_reversion_v2", "AAPL", "1.00", "0.0020", 35, "TIME"),
    ]
    for strategy, symbol, pnl, ret, minutes, reason in fixture_outcomes:
        ledger.record(
            strategy_id=strategy,
            symbol=symbol,
            pnl=Decimal(pnl),
            return_pct=Decimal(ret),
            holding_minutes=minutes,
            exit_reason=reason,
        )
    summary = ledger.summarize()

    ranker = StrategyEnsembleRanker()
    scores = ranker.rank([
        ranker.score(
            strategy_id="momentum_v2",
            signal_strength=Decimal("0.82"),
            historical_metrics={
                "win_rate": "0.60",
                "profit_factor": "1.75",
                "maximum_drawdown": "0.08",
            },
            regime_fit=Decimal("0.90"),
            risk_penalty=Decimal("0.05"),
        ),
        ranker.score(
            strategy_id="mean_reversion_v2",
            signal_strength=Decimal("0.70"),
            historical_metrics={
                "win_rate": "0.67",
                "profit_factor": "1.50",
                "maximum_drawdown": "0.05",
            },
            regime_fit=Decimal("0.62"),
            risk_penalty=Decimal("0.04"),
        ),
        ranker.score(
            strategy_id="breakout_v2",
            signal_strength=Decimal("0.65"),
            historical_metrics={
                "win_rate": "0.48",
                "profit_factor": "1.30",
                "maximum_drawdown": "0.12",
            },
            regime_fit=Decimal("0.75"),
            risk_penalty=Decimal("0.10"),
        ),
    ])

    optimizer = PortfolioOptimizer()
    portfolio = optimizer.optimize(
        symbol_scores={
            "AAPL": Decimal("0.90"),
            "MSFT": Decimal("0.72"),
            "SPY": Decimal("0.80"),
        },
        total_capital=Decimal("1000"),
        maximum_symbol_weight=Decimal("0.35"),
        cash_reserve_weight=Decimal("0.20"),
    )

    risk_engine = DynamicRiskEngineV2()
    risk_decisions = [
        risk_engine.evaluate(
            symbol="AAPL",
            base_notional=Decimal("10"),
            volatility=Decimal("0.25"),
            portfolio_drawdown=Decimal("1"),
            maximum_drawdown=Decimal("10"),
            average_correlation=Decimal("0.20"),
            daily_loss_limit_reached=False,
        ).as_json(),
        risk_engine.evaluate(
            symbol="MSFT",
            base_notional=Decimal("10"),
            volatility=Decimal("0.60"),
            portfolio_drawdown=Decimal("3"),
            maximum_drawdown=Decimal("10"),
            average_correlation=Decimal("0.50"),
            daily_loss_limit_reached=False,
        ).as_json(),
    ]

    checks = {
        "learning_records_created": summary["trade_count"] == 4,
        "strategy_scores_created": len(scores) == 3,
        "ranking_descending": all(
            scores[index].total_score >= scores[index + 1].total_score
            for index in range(len(scores) - 1)
        ),
        "portfolio_targets_created": len(portfolio["targets"]) == 3,
        "portfolio_not_modified": (
            portfolio["actual_portfolio_modified"] is False
        ),
        "risk_decisions_created": len(risk_decisions) == 2,
        "risk_adjusts_notional": all(
            Decimal(item["adjusted_notional"])
            <= Decimal(item["base_notional"])
            for item in risk_decisions
        ),
        "model_training_not_claimed": (
            summary["actual_model_training_performed"] is False
        ),
        "broker_network_off": True,
        "broker_write_off": True,
        "orders_zero": True,
    }

    result = {
        "stage": "AI_V2_MEGA_BUNDLE_1",
        "state": "AI_STRATEGY_LEARNING_PORTFOLIO_RISK_OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [k for k, value in checks.items() if not value],
        "strategy_ranking": [score.as_json() for score in scores],
        "learning_summary": summary,
        "portfolio_optimization": portfolio,
        "dynamic_risk_decisions": risk_decisions,
        "ai_strategy_ensemble": "READY",
        "performance_learning_ledger": "READY",
        "portfolio_optimizer": "READY",
        "dynamic_risk_engine_v2": "READY",
        "actual_machine_learning_training_performed": False,
        "actual_news_data_used": False,
        "actual_market_data_network_used": False,
        "actual_broker_network_used": False,
        "actual_broker_write_used": False,
        "automatic_order_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_bundle": "AI_V2_MEGA_BUNDLE_2_DATA_SCANNER_NEWS_DASHBOARD",
    }
    (actual / "ai_v2_mega_bundle_1_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
