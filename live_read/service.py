from __future__ import annotations
from hashlib import sha256
import json
from typing import Any

from .adapter import AlpacaLiveReadAdapter


def run_snapshot(
    adapter: AlpacaLiveReadAdapter,
    symbols: list[str],
    *,
    mode: str,
) -> dict[str, Any]:
    account = adapter.get_account()
    positions = adapter.get_positions()
    orders = adapter.get_open_orders()
    clock = adapter.get_clock()
    assets = [adapter.get_asset(symbol) for symbol in symbols]

    core = {
        "account": account,
        "positions": positions,
        "open_orders": orders,
        "clock": clock,
        "assets": assets,
    }
    snapshot_hash = sha256(
        json.dumps(core, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "stage": "L2",
        "state": "LIVE_READ_ONLY_PREPARATION_READY",
        "status": "PASS",
        "mode": mode,
        "account_status": account.get("status"),
        "account_id_present": bool(account.get("id")),
        "position_count": len(positions),
        "open_order_count": len(orders),
        "market_open": clock.get("is_open"),
        "asset_symbols": [a.get("symbol") for a in assets],
        "all_assets_tradable": all(a.get("tradable") for a in assets),
        "snapshot_hash": snapshot_hash,
        "live_network_enabled": False,
        "live_write_enabled": False,
        "actual_live_read_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_stage": (
            "L2_ACTUAL_LIVE_READ_ONLY_AFTER_P5_ACTUAL_PAPER_COMPLETION"
        ),
    }
