from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


def canonical_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _position(state: dict[str, Any], symbol: str) -> dict[str, Any]:
    positions = state.setdefault("positions", {})
    if symbol not in positions:
        positions[symbol] = {
            "symbol": symbol,
            "quantity": 0.0,
            "average_cost": 0.0,
            "market_price": 0.0,
            "market_value": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
        }
    return positions[symbol]


def _round(value: float) -> float:
    return round(float(value), 8)


def apply_fill(
    portfolio_state: dict[str, Any],
    fill_event: dict[str, Any],
    applied_fill_event_ids: set[str],
) -> dict[str, Any]:
    fill_event_id = str(fill_event.get("fill_event_id", "")).strip()
    symbol = str(fill_event.get("symbol", "")).strip()
    side = str(fill_event.get("side", "")).upper()
    fill_state = str(fill_event.get("fill_state", "")).upper()
    fill_price = fill_event.get("fill_price")
    filled_quantity = fill_event.get("filled_quantity")
    filled_notional = fill_event.get("filled_notional")

    checks = {
        "fill_event_id_present": bool(fill_event_id),
        "fill_event_version_valid": fill_event.get("fill_event_version") == "V392.11A",
        "simulated_fill": fill_event.get("simulated") is True,
        "paper_only": fill_event.get("target_environment") == "PAPER",
        "broker_adapter_none": fill_event.get("broker_adapter") == "NONE",
        "symbol_present": bool(symbol),
        "side_valid": side in {"BUY", "SELL"},
        "fill_state_supported": fill_state in {"FILLED", "PARTIALLY_FILLED", "NO_FILL"},
        "fill_price_positive": isinstance(fill_price, (int, float)) and fill_price > 0,
        "filled_quantity_nonnegative": (
            isinstance(filled_quantity, (int, float)) and filled_quantity >= 0
        ),
        "filled_notional_nonnegative": (
            isinstance(filled_notional, (int, float)) and filled_notional >= 0
        ),
        "fill_not_applied": fill_event_id not in applied_fill_event_ids,
        "cash_present": isinstance(portfolio_state.get("cash"), (int, float)),
        "portfolio_version_valid": (
            portfolio_state.get("portfolio_version") == "V392.12A"
        ),
    }

    if not all(checks.values()):
        return {
            "state": "FILL_ACCOUNTING_BLOCKED",
            "approved": False,
            "checks": checks,
            "failed": [name for name, passed in checks.items() if not passed],
            "replay_detected": not checks["fill_not_applied"],
            "portfolio_state": portfolio_state,
            "portfolio_hash": canonical_hash(portfolio_state),
            "accounting_event": {},
            "accounting_event_hash": "",
            "required_action": "DO_NOT_UPDATE_PORTFOLIO",
        }

    updated = json.loads(json.dumps(portfolio_state))
    position = _position(updated, symbol)

    qty = float(filled_quantity)
    price = float(fill_price)
    notional = float(filled_notional)

    previous_qty = float(position.get("quantity", 0.0))
    previous_avg = float(position.get("average_cost", 0.0))
    realized_delta = 0.0

    if fill_state == "NO_FILL" or qty == 0:
        cash_delta = 0.0
        new_qty = previous_qty
        new_avg = previous_avg
    elif side == "BUY":
        cash_delta = -notional
        new_qty = previous_qty + qty
        if new_qty > 0:
            total_cost = previous_qty * previous_avg + qty * price
            new_avg = total_cost / new_qty
        else:
            new_avg = 0.0
    else:
        sell_qty = min(qty, previous_qty)
        cash_delta = sell_qty * price
        realized_delta = (price - previous_avg) * sell_qty
        new_qty = previous_qty - sell_qty
        new_avg = previous_avg if new_qty > 0 else 0.0

    updated["cash"] = _round(float(updated["cash"]) + cash_delta)
    position["quantity"] = _round(new_qty)
    position["average_cost"] = _round(new_avg)
    position["market_price"] = _round(price)
    position["market_value"] = _round(new_qty * price)
    position["realized_pnl"] = _round(
        float(position.get("realized_pnl", 0.0)) + realized_delta
    )
    position["unrealized_pnl"] = _round((price - new_avg) * new_qty)

    updated["realized_pnl"] = _round(
        sum(float(p.get("realized_pnl", 0.0)) for p in updated["positions"].values())
    )
    updated["unrealized_pnl"] = _round(
        sum(float(p.get("unrealized_pnl", 0.0)) for p in updated["positions"].values())
    )
    updated["equity"] = _round(
        float(updated["cash"])
        + sum(float(p.get("market_value", 0.0)) for p in updated["positions"].values())
    )
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()

    accounting_event = {
        "accounting_event_version": "V392.12A",
        "fill_event_id": fill_event_id,
        "symbol": symbol,
        "side": side,
        "fill_state": fill_state,
        "filled_quantity": _round(qty),
        "fill_price": _round(price),
        "filled_notional": _round(notional),
        "cash_delta": _round(cash_delta),
        "position_quantity_before": _round(previous_qty),
        "position_quantity_after": _round(new_qty),
        "average_cost_before": _round(previous_avg),
        "average_cost_after": _round(new_avg),
        "realized_pnl_delta": _round(realized_delta),
        "portfolio_equity_after": updated["equity"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "state": "FILL_ACCOUNTING_APPLIED",
        "approved": True,
        "checks": checks,
        "failed": [],
        "replay_detected": False,
        "portfolio_state": updated,
        "portfolio_hash": canonical_hash(updated),
        "accounting_event": accounting_event,
        "accounting_event_hash": canonical_hash(accounting_event),
        "required_action": "ALLOW_PORTFOLIO_RECONCILIATION_STAGE",
    }
