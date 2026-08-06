from __future__ import annotations
from typing import Any

from .defaults import PROFILES, STRATEGIES


def _number(
    value: Any,
    *,
    minimum: float,
    maximum: float,
    name: str,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name}: NUMBER_REQUIRED"
        ) from exc
    if not minimum <= result <= maximum:
        raise ValueError(
            f"{name}: OUT_OF_RANGE_{minimum}_{maximum}"
        )
    return result


def _integer(
    value: Any,
    *,
    minimum: int,
    maximum: int,
    name: str,
) -> int:
    number = _number(
        value,
        minimum=minimum,
        maximum=maximum,
        name=name,
    )
    if not number.is_integer():
        raise ValueError(
            f"{name}: INTEGER_REQUIRED"
        )
    return int(number)


def validate_symbols(value: Any) -> list[str]:
    if isinstance(value, str):
        values = value.replace(",", " ").split()
    elif isinstance(value, list):
        values = value
    else:
        raise ValueError("symbols: LIST_REQUIRED")

    result = []
    for item in values:
        symbol = str(item).strip().upper()
        if not symbol:
            continue
        if not symbol.replace(
            ".", ""
        ).replace("-", "").isalnum():
            raise ValueError(
                f"symbols: INVALID_{symbol}"
            )
        if symbol not in result:
            result.append(symbol)

    if len(result) > 50:
        raise ValueError(
            "symbols: MAXIMUM_50"
        )
    return result


def validate_draft(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("OBJECT_REQUIRED")

    key = str(
        payload.get("profile_key")
        or "READ_ONLY"
    ).upper()
    if key not in PROFILES:
        raise ValueError("UNKNOWN_PROFILE")

    profile_input = payload.get("profile")
    if not isinstance(profile_input, dict):
        profile_input = {}

    profile = dict(PROFILES[key])
    profile.update({
        "trading_style": str(
            profile_input.get(
                "trading_style",
                profile["trading_style"],
            )
        ).upper(),
        "max_positions": _integer(
            profile_input.get(
                "max_positions",
                profile["max_positions"],
            ),
            minimum=0,
            maximum=50,
            name="max_positions",
        ),
        "max_position_percent": _number(
            profile_input.get(
                "max_position_percent",
                profile["max_position_percent"],
            ),
            minimum=0,
            maximum=100,
            name="max_position_percent",
        ),
        "max_daily_loss_percent": _number(
            profile_input.get(
                "max_daily_loss_percent",
                profile["max_daily_loss_percent"],
            ),
            minimum=0,
            maximum=20,
            name="max_daily_loss_percent",
        ),
        "cash_reserve_percent": _number(
            profile_input.get(
                "cash_reserve_percent",
                profile["cash_reserve_percent"],
            ),
            minimum=0,
            maximum=100,
            name="cash_reserve_percent",
        ),
        "allow_short": bool(
            profile_input.get(
                "allow_short",
                profile["allow_short"],
            )
        ),
        "allow_extended_hours": bool(
            profile_input.get(
                "allow_extended_hours",
                profile[
                    "allow_extended_hours"
                ],
            )
        ),
    })

    if (
        profile["max_position_percent"]
        * profile["max_positions"]
        > 100
        - profile["cash_reserve_percent"]
        + profile["max_position_percent"]
    ):
        raise ValueError(
            "RISK_ALLOCATION_EXCEEDS_AVAILABLE_CAPITAL"
        )

    capital_limit = _number(
        payload.get("capital_limit", 0),
        minimum=0,
        maximum=100_000_000,
        name="capital_limit",
    )
    symbols = validate_symbols(
        payload.get("symbols", [])
    )

    strategies_input = payload.get(
        "strategies",
        {},
    )
    if not isinstance(strategies_input, dict):
        raise ValueError(
            "strategies: OBJECT_REQUIRED"
        )

    strategies = {}
    for name, defaults in STRATEGIES.items():
        incoming = strategies_input.get(
            name,
            {},
        )
        if not isinstance(incoming, dict):
            incoming = {}
        item = dict(defaults)
        item.update(incoming)
        item["enabled"] = bool(
            item.get("enabled", False)
        )
        item["weight"] = _number(
            item.get("weight", 1),
            minimum=0,
            maximum=10,
            name=f"{name}.weight",
        )
        strategies[name] = item

    if key == "READ_ONLY":
        profile["max_positions"] = 0
        profile["max_position_percent"] = 0.0
        profile["max_daily_loss_percent"] = 0.0
        profile["cash_reserve_percent"] = 100.0
        capital_limit = 0.0

    return {
        "profile_key": key,
        "profile": profile,
        "account_scope": str(
            payload.get(
                "account_scope",
                "ALL_READ_ONLY",
            )
        ).upper(),
        "symbols": symbols,
        "capital_limit": capital_limit,
        "strategies": strategies,
        "execution": {
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "activation_enabled": False,
            "mode": "DRAFT_ONLY",
        },
    }
