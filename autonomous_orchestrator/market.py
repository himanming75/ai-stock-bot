from __future__ import annotations
from typing import Any

def inspect(fixture:dict[str,Any])->dict[str,Any]:
    clock=fixture.get("clock",{})
    return {
        "market_open":bool(clock.get("is_open",False)),
        "timestamp":clock.get("timestamp"),
        "next_open":clock.get("next_open"),
        "next_close":clock.get("next_close"),
    }
