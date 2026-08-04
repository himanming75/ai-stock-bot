from __future__ import annotations
from typing import Any

from .kelly import adjusted_kelly
from .position_sizing import size_positions


def apply_kelly(payload: dict[str, Any]) -> dict[str, Any]:
    base = size_positions(payload).to_dict()

    fraction = float(payload.get("kelly_fraction", 0.5))
    maximum_kelly_pct = float(payload.get("maximum_kelly_pct", 0.25))

    stats_by_symbol = {
        str(item["symbol"]).strip().upper(): item
        for item in payload.get("kelly_statistics", [])
    }

    adjusted_positions: list[dict[str, Any]] = []
    for position in base["positions"]:
        symbol = position["symbol"]
        stats = stats_by_symbol.get(symbol)
        if stats is None:
            raise ValueError(f"KELLY_STATISTICS_MISSING_{symbol}")

        kelly = adjusted_kelly(
            win_rate=float(stats["win_rate"]),
            average_win=float(stats["average_win"]),
            average_loss=float(stats["average_loss"]),
            fraction=fraction,
            maximum_kelly_pct=maximum_kelly_pct,
        )

        kelly_notional_limit = base["account_equity"] * kelly["capped_kelly_pct"]
        recommended_notional = min(
            float(position["recommended_notional"]),
            kelly_notional_limit,
        )
        quantity = (
            recommended_notional / float(position["reference_price"])
            if float(position["reference_price"]) > 0
            else 0.0
        )
        if not bool(payload.get("allow_fractional_shares", True)):
            quantity = float(int(quantity))
            recommended_notional = quantity * float(position["reference_price"])

        risk_at_stop = recommended_notional * float(position["stop_loss_pct"])
        effective_weight = recommended_notional / base["account_equity"]

        if recommended_notional + 0.01 < float(position["recommended_notional"]):
            binding = "KELLY_LIMIT"
        else:
            binding = position["binding_constraint"]

        output = dict(position)
        output.update({
            "reward_risk_ratio": kelly["reward_risk_ratio"],
            "full_kelly_pct": kelly["full_kelly_pct"],
            "kelly_fraction": round(fraction, 6),
            "fractional_kelly_pct": kelly["fractional_kelly_pct"],
            "capped_kelly_pct": kelly["capped_kelly_pct"],
            "kelly_notional_limit": round(kelly_notional_limit, 2),
            "recommended_notional": round(recommended_notional, 2),
            "recommended_quantity": round(quantity, 6),
            "effective_weight": round(effective_weight, 6),
            "risk_at_stop": round(risk_at_stop, 2),
            "binding_constraint": binding,
        })
        output["reasons"] = list(output.get("reasons", [])) + [
            f"Full Kelly is {kelly['full_kelly_pct']:.4f}.",
            f"Fractional Kelly is {kelly['fractional_kelly_pct']:.4f}.",
            f"Capped Kelly allocation is {kelly['capped_kelly_pct']:.4f}.",
            "Kelly-adjusted size is analytical only and cannot submit an order.",
        ]
        adjusted_positions.append(output)

    total_notional = round(sum(float(item["recommended_notional"]) for item in adjusted_positions), 2)
    total_risk = round(sum(float(item["risk_at_stop"]) for item in adjusted_positions), 2)

    base.update({
        "positions": adjusted_positions,
        "kelly_fraction": round(fraction, 6),
        "maximum_kelly_pct": round(maximum_kelly_pct, 6),
        "total_recommended_notional": total_notional,
        "total_effective_weight": round(total_notional / base["account_equity"], 6),
        "total_risk_at_stop": total_risk,
        "remaining_cash": round(base["account_equity"] - total_notional, 2),
    })
    return base
