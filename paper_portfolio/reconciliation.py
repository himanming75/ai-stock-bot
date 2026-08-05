from __future__ import annotations
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


def _round(value: float) -> float:
    return round(float(value), 8)


def reconcile_portfolio(
    portfolio_state: dict[str, Any],
    accounting_event: dict[str, Any],
    applied_fill_registry: dict[str, Any],
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    positions = portfolio_state.get("positions", {})
    applied_fill_ids = applied_fill_registry.get("applied_fill_event_ids", [])

    checks: dict[str, bool] = {
        "portfolio_version_valid": (
            portfolio_state.get("portfolio_version") == "V392.12A"
        ),
        "cash_numeric": isinstance(portfolio_state.get("cash"), (int, float)),
        "equity_numeric": isinstance(portfolio_state.get("equity"), (int, float)),
        "realized_pnl_numeric": isinstance(
            portfolio_state.get("realized_pnl"), (int, float)
        ),
        "unrealized_pnl_numeric": isinstance(
            portfolio_state.get("unrealized_pnl"), (int, float)
        ),
        "positions_object": isinstance(positions, dict),
        "registry_list": isinstance(applied_fill_ids, list),
        "registry_unique": (
            isinstance(applied_fill_ids, list)
            and len(applied_fill_ids) == len(set(applied_fill_ids))
        ),
        "accounting_event_present": isinstance(accounting_event, dict),
    }

    position_errors: list[str] = []
    total_market_value = 0.0
    total_realized = 0.0
    total_unrealized = 0.0

    if isinstance(positions, dict):
        for symbol, position in positions.items():
            qty = position.get("quantity")
            avg = position.get("average_cost")
            market_price = position.get("market_price")
            market_value = position.get("market_value")
            realized = position.get("realized_pnl")
            unrealized = position.get("unrealized_pnl")

            numeric_fields = {
                "quantity": qty,
                "average_cost": avg,
                "market_price": market_price,
                "market_value": market_value,
                "realized_pnl": realized,
                "unrealized_pnl": unrealized,
            }

            for name, value in numeric_fields.items():
                if not isinstance(value, (int, float)):
                    position_errors.append(f"{symbol}:{name}:NOT_NUMERIC")

            if not all(isinstance(v, (int, float)) for v in numeric_fields.values()):
                continue

            if qty < -tolerance:
                position_errors.append(f"{symbol}:NEGATIVE_QUANTITY")
            if avg < -tolerance:
                position_errors.append(f"{symbol}:NEGATIVE_AVERAGE_COST")
            if market_price < -tolerance:
                position_errors.append(f"{symbol}:NEGATIVE_MARKET_PRICE")

            expected_market_value = _round(qty * market_price)
            expected_unrealized = _round((market_price - avg) * qty)

            if abs(float(market_value) - expected_market_value) > tolerance:
                position_errors.append(f"{symbol}:MARKET_VALUE_MISMATCH")

            if abs(float(unrealized) - expected_unrealized) > tolerance:
                position_errors.append(f"{symbol}:UNREALIZED_PNL_MISMATCH")

            total_market_value += float(market_value)
            total_realized += float(realized)
            total_unrealized += float(unrealized)

    expected_equity = _round(float(portfolio_state.get("cash", 0.0)) + total_market_value)
    expected_realized = _round(total_realized)
    expected_unrealized = _round(total_unrealized)

    checks.update({
        "positions_valid": not position_errors,
        "equity_matches": (
            isinstance(portfolio_state.get("equity"), (int, float))
            and abs(float(portfolio_state["equity"]) - expected_equity) <= tolerance
        ),
        "realized_pnl_matches": (
            isinstance(portfolio_state.get("realized_pnl"), (int, float))
            and abs(float(portfolio_state["realized_pnl"]) - expected_realized)
            <= tolerance
        ),
        "unrealized_pnl_matches": (
            isinstance(portfolio_state.get("unrealized_pnl"), (int, float))
            and abs(float(portfolio_state["unrealized_pnl"]) - expected_unrealized)
            <= tolerance
        ),
        "cash_nonnegative": (
            isinstance(portfolio_state.get("cash"), (int, float))
            and float(portfolio_state["cash"]) >= -tolerance
        ),
    })

    fill_event_id = str(accounting_event.get("fill_event_id", "")).strip()
    event_present = bool(accounting_event)
    checks["accounting_fill_id_valid"] = (
        not event_present
        or (
            bool(fill_event_id)
            and fill_event_id in set(applied_fill_ids)
        )
    )

    errors = [
        name for name, passed in checks.items() if not passed
    ] + position_errors

    valid = not errors

    return {
        "state": (
            "PAPER_PORTFOLIO_RECONCILED"
            if valid
            else "PAPER_PORTFOLIO_RECONCILIATION_FAILED"
        ),
        "valid": valid,
        "checks": checks,
        "errors": errors,
        "position_errors": position_errors,
        "expected": {
            "equity": expected_equity,
            "realized_pnl": expected_realized,
            "unrealized_pnl": expected_unrealized,
            "total_market_value": _round(total_market_value),
        },
        "actual": {
            "cash": portfolio_state.get("cash"),
            "equity": portfolio_state.get("equity"),
            "realized_pnl": portfolio_state.get("realized_pnl"),
            "unrealized_pnl": portfolio_state.get("unrealized_pnl"),
            "position_count": len(positions) if isinstance(positions, dict) else 0,
            "applied_fill_count": (
                len(applied_fill_ids) if isinstance(applied_fill_ids, list) else 0
            ),
        },
        "portfolio_hash": canonical_hash(portfolio_state),
        "registry_hash": canonical_hash(applied_fill_registry),
        "accounting_event_hash": canonical_hash(accounting_event),
        "required_action": (
            "ALLOW_AUTONOMOUS_CYCLE_ORCHESTRATOR_STAGE"
            if valid
            else "BLOCK_AUTONOMOUS_CYCLE"
        ),
    }
