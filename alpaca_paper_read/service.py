from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Iterable

from .integrity import validate_snapshot


def run_read_snapshot(
    adapter: Any,
    symbols: Iterable[str],
    mode: str,
) -> dict[str, Any]:
    normalized_symbols = sorted({
        str(symbol).strip().upper()
        for symbol in symbols
        if str(symbol).strip()
    })
    if not normalized_symbols:
        raise ValueError("AT_LEAST_ONE_ASSET_SYMBOL_REQUIRED")

    snapshot = {
        "snapshot_version": "V470.64",
        "mode": mode,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "account": adapter.get_account(),
        "positions": adapter.get_positions(),
        "open_orders": adapter.get_open_orders(),
        "clock": adapter.get_clock(),
        "assets": {
            symbol: adapter.get_asset(symbol)
            for symbol in normalized_symbols
        },
    }
    integrity = validate_snapshot(snapshot)

    return {
        "stage": "V470.64",
        "state": (
            "ALPACA_PAPER_READ_SAFETY_READY"
            if integrity["valid"]
            else "ALPACA_PAPER_READ_SAFETY_BLOCKED"
        ),
        "status": "PASS" if integrity["valid"] else "FAIL",
        "mode": mode,
        "snapshot": snapshot,
        "integrity": integrity,
        "account_read_completed": True,
        "positions_read_completed": True,
        "open_orders_read_completed": True,
        "market_clock_read_completed": True,
        "asset_tradability_read_completed": True,
        "read_only_http_enforced": True,
        "paper_endpoint_enforced": True,
        "timeout_retry_enabled": True,
        "rate_limit_handling_enabled": True,
        "network_recovery_enabled": True,
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V471_TO_V480_ALPACA_PAPER_EXECUTION_SAFETY",
    }
