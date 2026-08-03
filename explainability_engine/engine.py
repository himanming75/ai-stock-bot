from __future__ import annotations

from typing import Any

from explainability_engine.comparison import compare_ranked_candidates
from explainability_engine.contributions import (
    portfolio_contributions,
    signal_contributions,
)
from explainability_engine.narrative import (
    portfolio_narrative,
    strategy_narrative,
)
from explainability_engine.risks import (
    detect_portfolio_risks,
    detect_strategy_risks,
)


def build_explainability_report(
    strategy_result: dict[str, Any],
    indicator_result: dict[str, Any],
    portfolio_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "strategy_explanation": {
            "narrative": strategy_narrative(
                strategy_result,
                indicator_result,
            ),
            "signal_contributions": signal_contributions(strategy_result),
            "risk_factors": detect_strategy_risks(
                strategy_result,
                indicator_result,
            ),
        },
        "portfolio_explanation": {
            "narrative": portfolio_narrative(portfolio_result),
            "allocation_contributions": portfolio_contributions(
                portfolio_result
            ),
            "comparisons": compare_ranked_candidates(portfolio_result),
            "risk_factors": detect_portfolio_risks(portfolio_result),
        },
        "limitations": [
            "The engine uses only supplied local JSON results.",
            "It does not use news, fundamentals, or external AI APIs.",
            "It does not predict guaranteed returns.",
            "It does not submit or approve broker orders.",
        ],
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
