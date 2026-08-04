from __future__ import annotations
from typing import Any

def estimate(candidate: dict[str, Any], quote: dict[str, Any]) -> dict[str, Any]:
    action = str(candidate.get("action", "BUY")).upper()
    reference = float(candidate.get("reference_price", quote.get("mid", 0)) or 0)
    expected = float(quote.get("ask" if action == "BUY" else "bid", reference) or reference)
    signed = expected - reference if action == "BUY" else reference - expected
    pct = signed / reference * 100 if reference else 0.0
    return {
        "reference_price": round(reference, 6),
        "expected_fill_price": round(expected, 6),
        "expected_slippage": round(signed, 6),
        "expected_slippage_pct": round(pct, 6),
    }
