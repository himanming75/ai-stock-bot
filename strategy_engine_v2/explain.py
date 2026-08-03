from __future__ import annotations

from strategy_engine_v2.models import SignalInput


def build_reasons(signals: list[SignalInput], decision: str) -> list[str]:
    enabled = [signal for signal in signals if signal.enabled]
    if not enabled:
        return ["No enabled signals were provided."]

    if decision == "BUY":
        ordered = sorted(enabled, key=lambda x: x.normalized_score(), reverse=True)
    elif decision == "SELL":
        ordered = sorted(enabled, key=lambda x: x.normalized_score())
    else:
        ordered = sorted(enabled, key=lambda x: abs(x.normalized_score()), reverse=True)

    reasons = []
    for signal in ordered[:5]:
        label = signal.reason.strip() or signal.name
        reasons.append(
            f"{signal.name}: {label} "
            f"(score={signal.normalized_score():.1f}, "
            f"weight={signal.normalized_weight():.2f})"
        )
    return reasons
