from __future__ import annotations
from typing import Any

from .kelly_sizing import apply_kelly
from .volatility import volatility_multiplier


def apply_volatility_scaling(payload: dict[str, Any]) -> dict[str, Any]:
    base = apply_kelly(payload)

    target_volatility = float(payload.get("target_volatility", 0.20))
    minimum_multiplier = float(payload.get("minimum_volatility_multiplier", 0.25))
    maximum_multiplier = float(payload.get("maximum_volatility_multiplier", 1.0))

    observed = {
        str(item["symbol"]).strip().upper(): float(item["annualized_volatility"])
        for item in payload.get("volatility_statistics", [])
    }

    adjusted_positions: list[dict[str, Any]] = []
    for position in base["positions"]:
        symbol = position["symbol"]
        if symbol not in observed:
            raise ValueError(f"VOLATILITY_STATISTICS_MISSING_{symbol}")

        observed_volatility = observed[symbol]
        multiplier = volatility_multiplier(
            target_volatility=target_volatility,
            observed_volatility=observed_volatility,
            minimum_multiplier=minimum_multiplier,
            maximum_multiplier=maximum_multiplier,
        )

        prior_notional = float(position["recommended_notional"])
        scaled_notional = prior_notional * multiplier
        price = float(position["reference_price"])
        quantity = scaled_notional / price if price else 0.0

        if not bool(payload.get("allow_fractional_shares", True)):
            quantity = float(int(quantity))
            scaled_notional = quantity * price

        risk_at_stop = scaled_notional * float(position["stop_loss_pct"])
        effective_weight = scaled_notional / float(base["account_equity"])

        binding = (
            "VOLATILITY_LIMIT"
            if scaled_notional + 0.01 < prior_notional
            else position["binding_constraint"]
        )

        output = dict(position)
        output.update({
            "target_volatility": round(target_volatility, 6),
            "observed_volatility": round(observed_volatility, 6),
            "volatility_multiplier": round(multiplier, 6),
            "pre_volatility_notional": round(prior_notional, 2),
            "recommended_notional": round(scaled_notional, 2),
            "recommended_quantity": round(quantity, 6),
            "effective_weight": round(effective_weight, 6),
            "risk_at_stop": round(risk_at_stop, 2),
            "binding_constraint": binding,
        })
        output["reasons"] = list(output.get("reasons", [])) + [
            f"Target annualized volatility is {target_volatility:.4f}.",
            f"Observed annualized volatility is {observed_volatility:.4f}.",
            f"Volatility multiplier is {multiplier:.4f}.",
            "Volatility-scaled size is analytical only and cannot submit an order.",
        ]
        adjusted_positions.append(output)

    total_notional = round(sum(float(item["recommended_notional"]) for item in adjusted_positions), 2)
    total_risk = round(sum(float(item["risk_at_stop"]) for item in adjusted_positions), 2)

    base.update({
        "positions": adjusted_positions,
        "target_volatility": round(target_volatility, 6),
        "minimum_volatility_multiplier": round(minimum_multiplier, 6),
        "maximum_volatility_multiplier": round(maximum_multiplier, 6),
        "total_recommended_notional": total_notional,
        "total_effective_weight": round(total_notional / float(base["account_equity"]), 6),
        "total_risk_at_stop": total_risk,
        "remaining_cash": round(float(base["account_equity"]) - total_notional, 2),
    })
    return base
