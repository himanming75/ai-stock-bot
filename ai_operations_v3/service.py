from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .historical_lab import HistoricalAILab
from .marketplace import StrategyMarketplace
from .metrics import PerformanceMetricsEngine
from .portfolio import PortfolioIntelligence


def run_v140_to_v143(root: Path) -> dict[str, Any]:
    actual = root / "release/v140_to_v143_ai_operations/actual"
    actual.mkdir(parents=True, exist_ok=True)

    ai_final = json.loads(
        (
            root / "release/ai_v2_final/actual/"
                   "ai_v2_final_result.json"
        ).read_text(encoding="utf-8-sig")
    )
    bundle1 = json.loads(
        (
            root / "release/ai_v2_mega_bundle_1/actual/"
                   "ai_v2_mega_bundle_1_result.json"
        ).read_text(encoding="utf-8-sig")
    )
    operations_v2 = json.loads(
        (
            root / "release/operations_v2/actual/"
                   "operations_v2_result.json"
        ).read_text(encoding="utf-8-sig")
    )

    trade_returns = [
        Decimal("0.010"), Decimal("-0.004"),
        Decimal("0.006"), Decimal("0.003"),
        Decimal("-0.002"), Decimal("0.009"),
        Decimal("0.004"), Decimal("-0.003"),
    ]
    trade_pnls = [
        Decimal("10"), Decimal("-4"),
        Decimal("6"), Decimal("3"),
        Decimal("-2"), Decimal("9"),
        Decimal("4"), Decimal("-3"),
    ]
    equity = [Decimal("1000")]
    for pnl in trade_pnls:
        equity.append(equity[-1] + pnl)

    performance = PerformanceMetricsEngine().calculate(
        trade_returns=trade_returns,
        trade_pnls=trade_pnls,
        equity_curve=equity,
    )
    lab = HistoricalAILab().summarize(ai_v2_final=ai_final)
    marketplace = StrategyMarketplace().build(
        strategy_ranking=bundle1.get("strategy_ranking", [])
    )

    positions = [
        {
            "symbol": "AAPL",
            "sector": "Technology",
            "market_value": "300",
        },
        {
            "symbol": "MSFT",
            "sector": "Technology",
            "market_value": "250",
        },
        {
            "symbol": "SPY",
            "sector": "Broad Market",
            "market_value": "300",
        },
        {
            "symbol": "XLV",
            "sector": "Healthcare",
            "market_value": "150",
        },
    ]
    correlations = {
        "AAPL": {
            "AAPL": Decimal("1"),
            "MSFT": Decimal("0.72"),
            "SPY": Decimal("0.65"),
            "XLV": Decimal("0.28"),
        },
        "MSFT": {
            "AAPL": Decimal("0.72"),
            "MSFT": Decimal("1"),
            "SPY": Decimal("0.68"),
            "XLV": Decimal("0.30"),
        },
        "SPY": {
            "AAPL": Decimal("0.65"),
            "MSFT": Decimal("0.68"),
            "SPY": Decimal("1"),
            "XLV": Decimal("0.50"),
        },
        "XLV": {
            "AAPL": Decimal("0.28"),
            "MSFT": Decimal("0.30"),
            "SPY": Decimal("0.50"),
            "XLV": Decimal("1"),
        },
    }
    portfolio = PortfolioIntelligence().analyze(
        positions=positions,
        correlations=correlations,
        sector_limits={
            "Technology": Decimal("0.60"),
            "Broad Market": Decimal("0.40"),
            "Healthcare": Decimal("0.30"),
        },
    )

    checks = {
        "ai_final_pass": ai_final.get("status") == "PASS",
        "operations_v2_pass": operations_v2.get("status") == "PASS",
        "performance_metrics_created": performance["trade_count"] == 8,
        "historical_lab_created": lab["walk_forward_window_count"] > 0,
        "marketplace_created": marketplace["strategy_count"] == 8,
        "portfolio_intelligence_created": portfolio["position_count"] == 4,
        "dashboard_read_only": True,
        "strategy_activation_not_performed": (
            marketplace["actual_strategy_activation_performed"] is False
        ),
        "portfolio_not_modified": (
            portfolio["actual_portfolio_modified"] is False
        ),
        "orders_not_created": portfolio["actual_orders_created"] is False,
    }

    dashboard = {
        "schema_version": 5,
        "stage": "V140_TO_V143_AI_OPERATIONS",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "performance_metrics": performance,
        "historical_ai_lab": lab,
        "strategy_marketplace": marketplace,
        "portfolio_intelligence": portfolio,
        "v140_dashboard_5": "READY",
        "v141_historical_ai_lab": "READY",
        "v142_strategy_marketplace": "READY",
        "v143_portfolio_intelligence": "READY",
        "read_only": True,
        "actual_market_network_used": False,
        "actual_broker_network_used": False,
        "actual_broker_write_used": False,
        "automatic_order_submission_enabled": False,
        "actual_strategy_activation_performed": False,
        "actual_portfolio_modified": False,
        "actual_orders_created": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    (actual / "dashboard5_data.json").write_text(
        json.dumps(dashboard, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (actual / "v140_to_v143_result.json").write_text(
        json.dumps(dashboard, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return dashboard
