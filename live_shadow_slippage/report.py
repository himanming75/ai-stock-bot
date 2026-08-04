from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from live_shadow_slippage.io import load_json, write_json

def build(root: Path, current: dict[str, Any]) -> dict[str, Any]:
    history_path = root / "release/v226_01_to_v230_64/actual/live_shadow_history.json"
    history = load_json(history_path)
    rows = history.get("rows", [])

    signal = current.get("signal", {})
    quote = current.get("quote", {})
    slippage = current.get("slippage", {})
    qualification = current.get("qualification", {})

    rows.append({
        "observed_at": current.get("observed_at"),
        "symbol": signal.get("symbol", quote.get("symbol", "UNKNOWN")),
        "slippage_pct": float(slippage.get("slippage_pct", 0) or 0),
        "spread_pct": float(quote.get("spread_pct", 0) or 0),
        "qualified": qualification.get("passed") is True,
        "score": float(qualification.get("score", 0) or 0),
    })
    history["rows"] = rows
    write_json(history_path, history)

    count = len(rows)
    qualified = sum(1 for row in rows if row["qualified"])
    avg_slippage = (
        sum(abs(float(row["slippage_pct"])) for row in rows) / count
        if count
        else 0
    )
    max_slippage = max(
        [abs(float(row["slippage_pct"])) for row in rows] or [0]
    )
    avg_spread = (
        sum(float(row["spread_pct"]) for row in rows) / count
        if count
        else 0
    )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_count": count,
        "qualified_count": qualified,
        "rejected_count": count - qualified,
        "qualification_rate_pct": (
            round(qualified / count * 100, 4)
            if count
            else 0
        ),
        "average_absolute_slippage_pct": round(avg_slippage, 6),
        "maximum_absolute_slippage_pct": round(max_slippage, 6),
        "average_spread_pct": round(avg_spread, 6),
        "actual_live_orders_submitted": 0,
    }
    write_json(
        root
        / "release/v226_01_to_v230_64/actual/"
        "daily_shadow_qualification_report.json",
        result,
    )
    return result
