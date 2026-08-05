from __future__ import annotations
import re


def normalize_equity_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    value = value.replace("/", ".")
    if not re.fullmatch(r"[A-Z0-9.\-]{1,20}", value):
        raise ValueError(f"invalid symbol: {symbol!r}")
    return value


def canonical_asset_key(broker: str, symbol: str, asset_class: str = "EQUITY") -> str:
    return f"{broker.upper()}::{asset_class.upper()}::{normalize_equity_symbol(symbol)}"
