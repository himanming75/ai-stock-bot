from __future__ import annotations
from typing import Any

def estimate(signal: dict[str, Any], quote: dict[str, Any]) -> dict[str, Any]:
    side = str(signal.get("side", "BUY")).upper()
    paper_price = float(signal.get("paper_reference_price", 0) or 0)
    expected_fill = quote["ask"] if side == "BUY" else quote["bid"]
    if expected_fill <= 0:
        expected_fill = quote["last"] or quote["mid"]
    absolute = expected_fill - paper_price
    signed = absolute if side == "BUY" else -absolute
    pct = signed / paper_price * 100 if paper_price > 0 else 0.0
    return {
        "side": side,
        "paper_reference_price": paper_price,
        "expected_live_fill_price": round(expected_fill, 6),
        "slippage_absolute": round(signed, 6),
        "slippage_pct": round(pct, 6),
    }
