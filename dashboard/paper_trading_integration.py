from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SNAPSHOT_RELATIVE_PATH = (
    "release/dash2_05/actual/current_paper_snapshot.json"
)
MAX_SNAPSHOT_AGE_SECONDS = 300


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _snapshot_age_seconds(snapshot: dict[str, Any]) -> int | None:
    raw = str(snapshot.get("observed_at", "")).strip()
    if not raw:
        return None
    try:
        observed = datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        )
    except ValueError:
        return None
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return max(
        0,
        int(
            (
                datetime.now(timezone.utc)
                - observed.astimezone(timezone.utc)
            ).total_seconds()
        ),
    )


def build_paper_trading_payload(
    root: Path,
) -> dict[str, Any]:
    snapshot_path = root / SNAPSHOT_RELATIVE_PATH
    snapshot = _load(snapshot_path)
    snapshot_age = _snapshot_age_seconds(snapshot)
    actual_snapshot = bool(
        snapshot.get("snapshot_type")
        == "ACTUAL_ALPACA_PAPER_READ_ONLY"
        and snapshot.get("paper_only") is True
        and snapshot.get("read_only") is True
    )
    snapshot_fresh = bool(
        actual_snapshot
        and snapshot_age is not None
        and snapshot_age <= MAX_SNAPSHOT_AGE_SECONDS
    )

    account = (
        snapshot.get("account", {})
        if actual_snapshot
        else {}
    )
    positions = (
        snapshot.get("positions", [])
        if actual_snapshot
        else []
    )
    open_orders = (
        snapshot.get("open_orders", [])
        if actual_snapshot
        else []
    )
    clock = (
        snapshot.get("clock", {})
        if actual_snapshot
        else {}
    )

    if not isinstance(account, dict):
        account = {}
    if not isinstance(positions, list):
        positions = []
    if not isinstance(open_orders, list):
        open_orders = []
    if not isinstance(clock, dict):
        clock = {}

    lifecycle = _load(
        root
        / "release/op3_09_to_op3_12/actual/"
        "paper_order_lifecycle_result.json"
    )
    limited = _load(
        root
        / "release/op3_13_to_op3_16/actual/"
        "limited_autonomous_paper_trading_result.json"
    )
    risk_source = _load(
        root
        / "release/op3_13_to_op3_16/input/"
        "limited_autonomous_risk_snapshot.json"
    )

    lifecycle_order = {
        "broker_order_id": lifecycle.get(
            "broker_order_id", ""
        ),
        "client_order_id": lifecycle.get(
            "client_order_id", ""
        ),
        "symbol": lifecycle.get("symbol", ""),
        "side": lifecycle.get("side", ""),
        "expected_qty": lifecycle.get(
            "expected_qty", 0
        ),
        "status": lifecycle.get("order_status", ""),
        "fill_state": lifecycle.get("fill_state", ""),
        "filled_qty": lifecycle.get("filled_qty", 0),
        "filled_avg_price": lifecycle.get(
            "filled_avg_price", 0
        ),
        "recovery_required": bool(
            lifecycle.get("recovery_required", False)
        ),
    }

    risk_reasons = list(
        limited.get("risk_reasons", [])
        if isinstance(limited.get("risk_reasons"), list)
        else []
    )
    if not snapshot_fresh:
        risk_reasons.append(
            "ACTUAL_PAPER_SNAPSHOT_MISSING_OR_STALE"
        )

    return {
        "dashboard_stage": "DASH2.05-HOTFIX",
        "snapshot": {
            "source": SNAPSHOT_RELATIVE_PATH,
            "actual": actual_snapshot,
            "fresh": snapshot_fresh,
            "age_seconds": snapshot_age,
            "maximum_age_seconds": (
                MAX_SNAPSHOT_AGE_SECONDS
            ),
            "observed_at": snapshot.get(
                "observed_at", ""
            ),
        },
        "account": {
            "status": (
                account.get("status", "NOT_AVAILABLE")
                if snapshot_fresh
                else "NOT_AVAILABLE"
            ),
            "cash": (
                _number(account.get("cash", 0))
                if snapshot_fresh else 0.0
            ),
            "buying_power": (
                _number(account.get("buying_power", 0))
                if snapshot_fresh else 0.0
            ),
            "portfolio_value": (
                _number(account.get("portfolio_value", 0))
                if snapshot_fresh else 0.0
            ),
            "equity": (
                _number(account.get("equity", 0))
                if snapshot_fresh else 0.0
            ),
            "account_blocked": (
                bool(account.get("account_blocked", False))
                if snapshot_fresh else False
            ),
            "trading_blocked": (
                bool(account.get("trading_blocked", False))
                if snapshot_fresh else False
            ),
        },
        "open_orders": [
            {
                "broker_order_id": item.get("id", ""),
                "client_order_id": item.get(
                    "client_order_id", ""
                ),
                "symbol": item.get("symbol", ""),
                "side": item.get("side", ""),
                "quantity": _number(item.get("qty", 0)),
                "filled_quantity": _number(
                    item.get("filled_qty", 0)
                ),
                "order_type": item.get(
                    "order_type",
                    item.get("type", ""),
                ),
                "time_in_force": item.get(
                    "time_in_force", ""
                ),
                "status": item.get("status", ""),
                "extended_hours": bool(
                    item.get("extended_hours", False)
                ),
            }
            for item in open_orders
            if snapshot_fresh and isinstance(item, dict)
        ],
        "order_lifecycle": lifecycle_order,
        "positions": [
            {
                "symbol": item.get("symbol", ""),
                "qty": _number(item.get("qty", 0)),
                "avg_entry_price": _number(
                    item.get("avg_entry_price", 0)
                ),
                "market_value": _number(
                    item.get("market_value", 0)
                ),
                "unrealized_pl": _number(
                    item.get("unrealized_pl", 0)
                ),
            }
            for item in positions
            if snapshot_fresh and isinstance(item, dict)
        ],
        "risk": {
            "daily_orders": int(
                risk_source.get("daily_orders", 0) or 0
            ),
            "open_positions": (
                len(positions) if snapshot_fresh else 0
            ),
            "open_orders": (
                len(open_orders) if snapshot_fresh else 0
            ),
            "daily_pnl": float(
                risk_source.get("daily_pnl", 0) or 0
            ),
            "consecutive_losses": int(
                risk_source.get(
                    "consecutive_losses", 0
                ) or 0
            ),
            "minutes_to_market_close": int(
                risk_source.get(
                    "minutes_to_market_close", 0
                ) or 0
            ),
            "emergency_stop_engaged": bool(
                risk_source.get(
                    "emergency_stop_engaged", False
                )
            ),
            "market_open": (
                bool(clock.get("is_open", False))
                if snapshot_fresh else False
            ),
            "latest_decision": limited.get(
                "approved_action", "HOLD"
            ),
            "risk_ready": bool(
                limited.get("risk_ready", False)
                and snapshot_fresh
            ),
            "risk_reasons": risk_reasons,
        },
        "runtime": {
            "state": limited.get(
                "state", "NOT_AVAILABLE"
            ),
            "status": limited.get("status", "UNKNOWN"),
            "single_cycle_only": bool(
                limited.get("single_cycle_only", True)
            ),
            "continuous_loop_enabled": bool(
                limited.get(
                    "continuous_loop_enabled", False
                )
            ),
            "actual_paper_orders_submitted": int(
                limited.get(
                    "actual_paper_orders_submitted", 0
                ) or 0
            ),
            "live_orders_submitted": int(
                limited.get("live_orders_submitted", 0)
                or 0
            ),
        },
        "read_only": True,
        "order_controls_available": False,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
    }


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
