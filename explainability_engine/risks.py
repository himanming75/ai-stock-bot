from __future__ import annotations

from typing import Any


def detect_strategy_risks(
    strategy_result: dict[str, Any],
    indicator_result: dict[str, Any],
) -> list[dict[str, Any]]:
    risks = []
    decision = strategy_result.get("decision", {})
    indicators = indicator_result.get("indicators", {})

    confidence = float(decision.get("confidence", 0))
    if confidence < 50:
        risks.append({
            "severity": "MEDIUM",
            "code": "LOW_CONFIDENCE",
            "message": f"Decision confidence is only {confidence:.2f}%.",
        })

    rsi = indicators.get("rsi_14")
    if rsi is not None and float(rsi) >= 70:
        risks.append({
            "severity": "HIGH",
            "code": "RSI_OVERBOUGHT",
            "message": f"RSI(14) is {float(rsi):.2f}, indicating an overbought condition.",
        })
    elif rsi is not None and float(rsi) <= 30:
        risks.append({
            "severity": "MEDIUM",
            "code": "RSI_OVERSOLD",
            "message": f"RSI(14) is {float(rsi):.2f}, indicating an oversold condition.",
        })

    atr = indicators.get("atr_14")
    close = indicators.get("close")
    if atr is not None and close:
        atr_pct = float(atr) / float(close) * 100.0
        if atr_pct >= 3:
            risks.append({
                "severity": "HIGH",
                "code": "HIGH_ATR_VOLATILITY",
                "message": f"ATR is {atr_pct:.2f}% of price.",
            })

    histogram = indicators.get("macd_histogram")
    composite = float(decision.get("composite_score", 0))
    if histogram is not None:
        if composite > 0 and float(histogram) < 0:
            risks.append({
                "severity": "MEDIUM",
                "code": "MACD_DIVERGENCE",
                "message": "Composite score is bullish while MACD histogram is negative.",
            })
        elif composite < 0 and float(histogram) > 0:
            risks.append({
                "severity": "MEDIUM",
                "code": "MACD_DIVERGENCE",
                "message": "Composite score is bearish while MACD histogram is positive.",
            })

    if not risks:
        risks.append({
            "severity": "LOW",
            "code": "NO_MAJOR_TECHNICAL_RISK",
            "message": "No major technical risk was detected from the available indicators.",
        })
    return risks


def detect_portfolio_risks(portfolio_result: dict[str, Any]) -> list[dict[str, Any]]:
    portfolio = portfolio_result.get("portfolio", {})
    summary = portfolio.get("allocation_summary", {})
    sector_allocations = summary.get("sector_allocations_pct", {})
    risks = []

    sector_limit = float(summary.get("sector_limit_pct", 100))
    for sector, allocation in sector_allocations.items():
        value = float(allocation)
        if value >= sector_limit * 0.95:
            risks.append({
                "severity": "MEDIUM",
                "code": "SECTOR_LIMIT_NEAR_CAP",
                "message": f"{sector} allocation is {value:.2f}% near the {sector_limit:.2f}% cap.",
            })

    allocations = portfolio.get("recommended_allocations", [])
    for row in allocations:
        volatility = float(row.get("volatility_pct", 0))
        if volatility >= 6:
            risks.append({
                "severity": "HIGH",
                "code": "HIGH_VOLATILITY_POSITION",
                "message": (
                    f"{row.get('symbol')} has volatility of {volatility:.2f}% "
                    f"with allocation {float(row.get('recommended_weight_pct', 0)):.2f}%."
                ),
            })

    allocated = float(summary.get("allocated_pct", 0))
    limit = float(summary.get("portfolio_exposure_limit_pct", 0))
    if limit and allocated >= limit * 0.95:
        risks.append({
            "severity": "MEDIUM",
            "code": "PORTFOLIO_EXPOSURE_NEAR_CAP",
            "message": f"Portfolio allocation is {allocated:.2f}% near the {limit:.2f}% limit.",
        })

    if not risks:
        risks.append({
            "severity": "LOW",
            "code": "NO_MAJOR_PORTFOLIO_RISK",
            "message": "No major portfolio concentration risk was detected.",
        })
    return risks
