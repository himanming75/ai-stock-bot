from __future__ import annotations

from typing import Any


def strategy_narrative(
    strategy_result: dict[str, Any],
    indicator_result: dict[str, Any],
) -> str:
    decision = strategy_result.get("decision", {})
    indicators = indicator_result.get("indicators", {})
    symbol = decision.get("symbol", indicators.get("symbol", "UNKNOWN"))
    action = decision.get("decision", "HOLD")
    confidence = float(decision.get("confidence", 0))
    score = float(decision.get("composite_score", 0))

    return (
        f"{symbol} is classified as {action} with {confidence:.2f}% confidence "
        f"and a composite score of {score:.2f}. "
        f"The latest close is {float(indicators.get('close', 0)):.2f}, "
        f"RSI(14) is {float(indicators.get('rsi_14', 0)):.2f}, and "
        f"the MACD histogram is {float(indicators.get('macd_histogram', 0)):.6f}. "
        "This explanation is descriptive only and does not submit an order."
    )


def portfolio_narrative(portfolio_result: dict[str, Any]) -> str:
    portfolio = portfolio_result.get("portfolio", {})
    summary = portfolio.get("allocation_summary", {})
    allocations = portfolio.get("recommended_allocations", [])
    symbols = ", ".join(
        str(row.get("symbol")) for row in allocations[:5]
    ) or "none"

    return (
        f"The portfolio engine ranked {int(portfolio.get('ranked_count', 0))} candidates "
        f"and recommended {len(allocations)} allocations totaling "
        f"{float(summary.get('allocated_pct', 0)):.2f}% of capital. "
        f"The portfolio score is {float(portfolio.get('portfolio_score', 0)):.2f} "
        f"and the diversification score is "
        f"{float(portfolio.get('diversification_score', 0)):.2f}. "
        f"Recommended symbols are {symbols}. "
        "These are paper-only model allocations, not executable orders."
    )
