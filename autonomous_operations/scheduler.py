from __future__ import annotations


def scheduler_state(
    *,
    market_open: bool,
    current_stage: str,
    emergency_stop: bool,
) -> dict:
    if emergency_stop:
        return {
            "state": "EMERGENCY_STOPPED",
            "next_stage": "MANUAL_REVIEW",
            "market_open": market_open,
        }

    if not market_open:
        return {
            "state": "WAITING_FOR_MARKET_OPEN",
            "next_stage": "MARKET_OPEN_CHECK",
            "market_open": False,
        }

    sequence = [
        "MARKET_DATA",
        "AI_BRAIN",
        "MULTI_AI_VOTING",
        "RISK_ENGINE",
        "PORTFOLIO_AI",
        "BROKER_ADAPTER",
        "SELF_LEARNING",
        "LEDGER",
    ]
    try:
        index = sequence.index(current_stage)
        next_stage = (
            sequence[index + 1]
            if index + 1 < len(sequence)
            else "CYCLE_COMPLETE"
        )
    except ValueError:
        next_stage = "MARKET_DATA"

    return {
        "state": "RUNNING",
        "next_stage": next_stage,
        "market_open": True,
    }
