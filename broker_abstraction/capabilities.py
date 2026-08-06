from __future__ import annotations

CAPABILITIES = {
    "ALPACA": {
        "accounts_read": True,
        "positions_read": True,
        "orders_read": True,
        "quotes_read": True,
        "market_clock_read": True,
        "fractional": True,
        "options": False,
        "crypto": True,
        "shorting": True,
        "extended_hours": True,
        "write_enabled": False,
    },
    "ETRADE": {
        "accounts_read": True,
        "positions_read": True,
        "orders_read": True,
        "quotes_read": True,
        "market_clock_read": False,
        "fractional": False,
        "options": True,
        "crypto": False,
        "shorting": True,
        "extended_hours": True,
        "write_enabled": False,
    },
}


def get_capabilities(broker: str) -> dict:
    name = broker.upper()
    if name not in CAPABILITIES:
        raise ValueError("UNKNOWN_BROKER")
    return dict(CAPABILITIES[name])
