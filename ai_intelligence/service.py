from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .dashboard_model import DashboardV2ModelBuilder
from .events import EarningsEventFramework, EventScoringFramework
from .explanation import StrategyExplanationEngine
from .historical_adapter import HistoricalDataAdapter
from .regime import MarketRegimeDetector
from .scanner import StockScanner
from .sector import SectorRotationAnalyzer


def run_intelligence_platform(root: Path) -> dict[str, Any]:
    actual = root / "release/ai_v2_mega_bundle_2/actual"
    actual.mkdir(parents=True, exist_ok=True)

    bundle_1_path = (
        root / "release/ai_v2_mega_bundle_1/actual/"
               "ai_v2_mega_bundle_1_result.json"
    )
    bundle_1 = json.loads(bundle_1_path.read_text(encoding="utf-8-sig"))

    regime = MarketRegimeDetector().detect({
        "index_return_20": "0.06",
        "volatility_20": "0.11",
        "breadth": "0.68",
        "trend_strength": "0.75",
    })
    regime_multiplier = Decimal(regime["allocation_multiplier"])

    sectors = SectorRotationAnalyzer().rank({
        "Technology": {
            "return_5": "0.025",
            "return_20": "0.08",
            "breadth": "0.72",
        },
        "Healthcare": {
            "return_5": "0.010",
            "return_20": "0.035",
            "breadth": "0.61",
        },
        "Financials": {
            "return_5": "-0.005",
            "return_20": "0.015",
            "breadth": "0.48",
        },
    })
    sector_scores = {
        row["sector"]: Decimal(row["score"]) for row in sectors
    }

    adapter = HistoricalDataAdapter()
    scanner = StockScanner()
    event_engine = EventScoringFramework()
    earnings_engine = EarningsEventFramework()
    explainer = StrategyExplanationEngine()

    definitions = [
        ("AAPL", "Technology", Decimal("180"), Decimal("0.8"), 10),
        ("MSFT", "Technology", Decimal("390"), Decimal("0.4"), 5),
        ("SPY", "Financials", Decimal("500"), Decimal("0.1"), None),
        ("XLV", "Healthcare", Decimal("140"), Decimal("0.3"), 20),
    ]

    rows = []
    explanations = []
    event_results = {}
    earnings_results = {}

    for symbol, sector, start_price, event_sentiment, earnings_days in definitions:
        events = event_engine.score([
            {
                "event_type": "OFFLINE_NEWS_FIXTURE",
                "severity": "MEDIUM",
                "sentiment": str(event_sentiment),
                "source_mode": "OFFLINE_FIXTURE",
            }
        ])
        earnings = earnings_engine.evaluate(
            days_until_earnings=earnings_days,
            surprise_history=Decimal("0.08"),
        )
        event_results[symbol] = events
        earnings_results[symbol] = earnings

        event_score = Decimal(events["event_score"])
        if earnings["block_new_position"]:
            event_score = min(event_score, Decimal("0.20"))

        row = scanner.score_symbol(
            symbol=symbol,
            bars=adapter.fixture_bars(start_price=start_price),
            sector_score=sector_scores.get(sector, Decimal("0.5")),
            event_score=event_score,
            regime_multiplier=regime_multiplier,
        )
        row["sector"] = sector
        row["earnings"] = earnings
        rows.append(row)

    ranking = scanner.rank(rows)
    for row in ranking:
        symbol = row["symbol"]
        explanations.append(explainer.explain(
            scanner_row=row,
            regime=regime,
            event_result=event_results[symbol],
            earnings=earnings_results[symbol],
        ))

    dashboard = DashboardV2ModelBuilder().build(
        regime=regime,
        scanner_ranking=ranking,
        sector_ranking=sectors,
        explanations=explanations,
        ai_v2_bundle_1=bundle_1,
    )
    (actual / "dashboard_v2_data.json").write_text(
        json.dumps(dashboard, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (actual / "watchlist_ranking.json").write_text(
        json.dumps(ranking, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (actual / "strategy_explanations.json").write_text(
        json.dumps(explanations, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checks = {
        "bundle_1_pass": bundle_1.get("status") == "PASS",
        "regime_detected": bool(regime.get("regime")),
        "four_symbols_scanned": len(ranking) == 4,
        "ranking_descending": all(
            Decimal(ranking[index]["total_score"])
            >= Decimal(ranking[index + 1]["total_score"])
            for index in range(len(ranking) - 1)
        ),
        "sector_ranking_created": len(sectors) == 3,
        "event_scores_created": len(event_results) == 4,
        "earnings_framework_used": len(earnings_results) == 4,
        "explanations_created": len(explanations) == 4,
        "dashboard_v2_created": dashboard["schema_version"] == 2,
        "dashboard_read_only": dashboard["read_only"] is True,
        "external_news_api_unused": all(
            result["external_news_api_used"] is False
            for result in event_results.values()
        ),
        "llm_api_unused": all(
            explanation["llm_api_used"] is False
            for explanation in explanations
        ),
        "broker_actions_unavailable": (
            dashboard["broker_actions_available"] is False
        ),
        "submission_off": (
            dashboard["automatic_order_submission_enabled"] is False
        ),
    }

    result = {
        "stage": "AI_V2_MEGA_BUNDLE_2",
        "state": "INTELLIGENCE_PLATFORM_OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "market_regime": regime,
        "scanner_ranking": ranking,
        "sector_ranking": sectors,
        "event_results": event_results,
        "earnings_results": earnings_results,
        "strategy_explanations": explanations,
        "dashboard_v2": dashboard,
        "stock_scanner": "READY",
        "technical_indicator_engine": "READY",
        "market_regime_detector": "READY",
        "news_event_framework": "READY_OFFLINE_ONLY",
        "earnings_event_framework": "READY",
        "sector_rotation_analyzer": "READY",
        "watchlist_ranking": "READY",
        "strategy_explanation_engine": "READY",
        "dashboard_v2_data_model": "READY",
        "historical_data_adapter": "READY",
        "actual_external_news_api_used": False,
        "actual_llm_api_used": False,
        "actual_market_network_used": False,
        "actual_broker_network_used": False,
        "actual_broker_write_used": False,
        "automatic_order_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_bundle": "AI_V2_MEGA_BUNDLE_3_ADVANCED_RESEARCH_FINAL",
    }
    (actual / "ai_v2_mega_bundle_2_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
