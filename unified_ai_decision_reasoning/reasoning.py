from __future__ import annotations


def reason_line(label: str, score: float, detail: str) -> str:
    direction = (
        "supports"
        if score > 0.08
        else "opposes"
        if score < -0.08
        else "is neutral for"
    )
    return (
        f"{label} {direction} the candidate "
        f"(score={score:.3f}): {detail}"
    )


def build_reasoning(
    *,
    symbol: str,
    component_scores: dict,
    missing_components: list[str],
    blockers: list[str],
    confidence: float,
    final_signal: str,
) -> dict:
    details = {
        "technical": "price, momentum, volatility and strategy evidence",
        "news_earnings_macro": "news sentiment, earnings and macro evidence",
        "fundamental": "valuation, quality, growth and balance-sheet evidence",
        "sector": "relative sector strength and rotation evidence",
        "options": "options positioning, volatility and event-risk evidence",
    }

    supporting = []
    opposing = []
    neutral = []
    for name, score in component_scores.items():
        line = reason_line(name, score, details.get(name, "model evidence"))
        if score > 0.08:
            supporting.append(line)
        elif score < -0.08:
            opposing.append(line)
        else:
            neutral.append(line)

    summary = (
        f"{symbol}: {final_signal} with confidence {confidence:.1f}%. "
        f"Supporting components={len(supporting)}, "
        f"opposing components={len(opposing)}, "
        f"neutral components={len(neutral)}."
    )
    if missing_components:
        summary += (
            " Missing inputs reduced confidence: "
            + ", ".join(sorted(missing_components))
            + "."
        )
    if blockers:
        summary += (
            " Decision blockers: "
            + ", ".join(sorted(blockers))
            + "."
        )

    return {
        "summary": summary,
        "supporting_reasons": supporting,
        "opposing_reasons": opposing,
        "neutral_reasons": neutral,
        "missing_input_explanation": missing_components,
        "blocker_explanation": blockers,
        "reasoning_mode": "DETERMINISTIC_TEMPLATE_NO_EXTERNAL_LLM",
    }
