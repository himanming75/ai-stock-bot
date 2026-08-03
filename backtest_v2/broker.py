from __future__ import annotations


def apply_buy_fill(price: float, slippage_bps: float) -> tuple[float, float]:
    slippage = price * (slippage_bps / 10000.0)
    return price + slippage, slippage


def apply_sell_fill(price: float, slippage_bps: float) -> tuple[float, float]:
    slippage = price * (slippage_bps / 10000.0)
    return price - slippage, slippage


def commission_for(notional: float, commission_bps: float) -> float:
    return abs(notional) * (commission_bps / 10000.0)
