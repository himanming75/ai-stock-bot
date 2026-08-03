from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object required: {path}")
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"JSON object required in {path}")
        records.append(value)
    return records


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def default_portfolio(initial_cash: float) -> dict[str, Any]:
    return {
        "cash": round(initial_cash, 8),
        "realized_pnl": 0.0,
        "positions": {},
        "processed_fill_ids": [],
    }


def _position(positions: dict[str, Any], symbol: str) -> dict[str, Any]:
    raw = positions.get(symbol, {})
    return {
        "quantity": float(raw.get("quantity", 0.0) or 0.0),
        "average_price": float(raw.get("average_price", 0.0) or 0.0),
        "market_price": float(raw.get("market_price", 0.0) or 0.0),
        "realized_pnl": float(raw.get("realized_pnl", 0.0) or 0.0),
    }


def apply_fill(
    portfolio: dict[str, Any],
    fill: dict[str, Any],
) -> dict[str, Any]:
    symbol = str(fill.get("symbol", "")).upper()
    side = str(fill.get("side", "")).upper()
    quantity = float(fill.get("quantity", 0.0) or 0.0)
    fill_price = float(fill.get("fill_price", 0.0) or 0.0)
    commission = float(fill.get("commission", 0.0) or 0.0)

    if not symbol or side not in {"BUY", "SELL"}:
        raise ValueError("Valid symbol and BUY/SELL side required")
    if quantity <= 0 or fill_price <= 0:
        raise ValueError("Positive quantity and fill price required")

    positions = dict(portfolio.get("positions", {}))
    current = _position(positions, symbol)
    cash = float(portfolio.get("cash", 0.0) or 0.0)
    portfolio_realized = float(
        portfolio.get("realized_pnl", 0.0) or 0.0
    )

    if side == "BUY":
        new_quantity = current["quantity"] + quantity
        weighted_cost = (
            current["quantity"] * current["average_price"]
            + quantity * fill_price
        )
        new_average = weighted_cost / new_quantity
        cash -= quantity * fill_price + commission
        current.update({
            "quantity": round(new_quantity, 8),
            "average_price": round(new_average, 8),
            "market_price": round(fill_price, 8),
        })
    else:
        if quantity > current["quantity"]:
            raise ValueError(
                f"Insufficient shadow position for {symbol}: "
                f"{current['quantity']} < {quantity}"
            )
        realized = (
            fill_price - current["average_price"]
        ) * quantity - commission
        new_quantity = current["quantity"] - quantity
        cash += quantity * fill_price - commission
        portfolio_realized += realized
        current["realized_pnl"] += realized
        current.update({
            "quantity": round(new_quantity, 8),
            "market_price": round(fill_price, 8),
            "realized_pnl": round(current["realized_pnl"], 8),
        })
        if new_quantity == 0:
            current["average_price"] = 0.0

    positions[symbol] = current
    portfolio["cash"] = round(cash, 8)
    portfolio["realized_pnl"] = round(portfolio_realized, 8)
    portfolio["positions"] = positions
    return portfolio


def mark_to_market(
    portfolio: dict[str, Any],
    market_prices: dict[str, float],
) -> dict[str, Any]:
    positions = dict(portfolio.get("positions", {}))
    market_value = 0.0
    unrealized_pnl = 0.0
    gross_exposure = 0.0

    for symbol, raw in positions.items():
        position = _position(positions, symbol)
        market_price = float(
            market_prices.get(
                symbol,
                position["market_price"] or position["average_price"],
            )
        )
        quantity = position["quantity"]
        value = quantity * market_price
        unrealized = (
            market_price - position["average_price"]
        ) * quantity
        position.update({
            "market_price": round(market_price, 8),
            "market_value": round(value, 8),
            "unrealized_pnl": round(unrealized, 8),
        })
        positions[symbol] = position
        market_value += value
        gross_exposure += abs(value)
        unrealized_pnl += unrealized

    cash = float(portfolio.get("cash", 0.0) or 0.0)
    equity = cash + market_value
    exposure_pct = (
        gross_exposure / equity * 100.0 if equity > 0 else 0.0
    )

    portfolio["positions"] = positions
    portfolio["market_value"] = round(market_value, 8)
    portfolio["unrealized_pnl"] = round(unrealized_pnl, 8)
    portfolio["equity"] = round(equity, 8)
    portfolio["gross_exposure"] = round(gross_exposure, 8)
    portfolio["gross_exposure_pct"] = round(exposure_pct, 8)
    portfolio["position_count"] = sum(
        1
        for position in positions.values()
        if float(position.get("quantity", 0.0) or 0.0) != 0
    )
    return portfolio


def run_shadow_portfolio(
    *,
    execution_result_path: Path,
    fill_ledger_path: Path,
    policy_path: Path,
    portfolio_state_path: Path,
    market_prices_path: Path,
    equity_history_path: Path,
    daily_report_path: Path,
    dashboard_path: Path,
    recovery_snapshot_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    try:
        execution = load_json(execution_result_path)
    except Exception as exc:
        execution = {}
        issues.append({
            "code": "INVALID_EXECUTION_RESULT",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        fills = load_jsonl(fill_ledger_path)
    except Exception as exc:
        fills = []
        issues.append({
            "code": "INVALID_FILL_LEDGER",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_PORTFOLIO_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "PORTFOLIO_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    safety = (
        ("SHADOW_ONLY_REQUIRED", bool(policy.get("shadow_only", False))),
        (
            "BROKER_WRITE_MUST_BE_DISABLED",
            not bool(policy.get("broker_write_enabled", True)),
        ),
        (
            "LIVE_TRADING_MUST_BE_DISABLED",
            not bool(policy.get("live_trading_enabled", True)),
        ),
    )
    for code, passed in safety:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "portfolio policy safety gate failed",
            })

    initial_cash = float(policy.get("initial_cash", 100000.0))
    maximum_gross_exposure_pct = float(
        policy.get("maximum_gross_exposure_pct", 100.0)
    )
    maximum_symbol_exposure_pct = float(
        policy.get("maximum_symbol_exposure_pct", 50.0)
    )

    if portfolio_state_path.exists():
        try:
            portfolio = load_json(portfolio_state_path)
        except Exception as exc:
            portfolio = default_portfolio(initial_cash)
            issues.append({
                "code": "INVALID_PORTFOLIO_STATE",
                "blocking": True,
                "detail": str(exc),
            })
    else:
        portfolio = default_portfolio(initial_cash)

    processed = set(portfolio.get("processed_fill_ids", []))
    new_fill_count = 0

    for fill in fills:
        fill_id = str(fill.get("fill_id", ""))
        if not fill_id or fill_id in processed:
            continue
        try:
            portfolio = apply_fill(portfolio, fill)
        except Exception as exc:
            issues.append({
                "code": "FILL_APPLICATION_FAILED",
                "blocking": True,
                "detail": f"{fill_id}: {exc}",
            })
            break
        processed.add(fill_id)
        new_fill_count += 1

    portfolio["processed_fill_ids"] = sorted(processed)

    try:
        market_prices_raw = load_json(market_prices_path)
    except Exception as exc:
        market_prices_raw = {}
        issues.append({
            "code": "INVALID_MARKET_PRICES",
            "blocking": True,
            "detail": str(exc),
        })

    market_prices = {
        str(symbol).upper(): float(price)
        for symbol, price in market_prices_raw.items()
        if isinstance(price, (int, float))
    }
    portfolio = mark_to_market(portfolio, market_prices)

    symbol_exposures: dict[str, float] = {}
    equity = float(portfolio.get("equity", 0.0) or 0.0)
    for symbol, position in portfolio["positions"].items():
        value = abs(float(position.get("market_value", 0.0) or 0.0))
        symbol_exposures[symbol] = round(
            value / equity * 100.0 if equity > 0 else 0.0,
            8,
        )

    risk_reasons: list[str] = []
    if portfolio["gross_exposure_pct"] > maximum_gross_exposure_pct:
        risk_reasons.append("MAXIMUM_GROSS_EXPOSURE_EXCEEDED")
    if any(
        exposure > maximum_symbol_exposure_pct
        for exposure in symbol_exposures.values()
    ):
        risk_reasons.append("MAXIMUM_SYMBOL_EXPOSURE_EXCEEDED")

    now = datetime.now(timezone.utc).isoformat()
    blocking = any(item.get("blocking") for item in issues)
    execution_ready = execution.get("state") in {
        "SHADOW_EXECUTION_FILLED",
        "SHADOW_EXECUTION_NO_ACTION",
    }

    if blocking:
        state, status = "SHADOW_PORTFOLIO_SAFE_MODE", "BLOCKED"
    elif not execution_ready:
        state, status = "WAIT_SHADOW_EXECUTION", "PASS"
    elif risk_reasons:
        state, status = "SHADOW_PORTFOLIO_RISK_LIMIT", "PASS"
    elif new_fill_count > 0:
        state, status = "SHADOW_PORTFOLIO_UPDATED", "PASS"
    else:
        state, status = "SHADOW_PORTFOLIO_NO_CHANGE", "PASS"

    portfolio.update({
        "stage": "V81.09",
        "symbol_exposures_pct": symbol_exposures,
        "risk_reasons": risk_reasons,
        "observed_at": now,
        "shadow_only": True,
        "broker_action_performed": False,
    })
    write_json(portfolio_state_path, portfolio)

    equity_point = {
        "stage": "V81.10",
        "equity": portfolio["equity"],
        "cash": portfolio["cash"],
        "market_value": portfolio["market_value"],
        "realized_pnl": portfolio["realized_pnl"],
        "unrealized_pnl": portfolio["unrealized_pnl"],
        "observed_at": now,
    }
    append_jsonl(equity_history_path, equity_point)

    daily_report = {
        "stage": "V81.11",
        "state": state,
        "new_fill_count": new_fill_count,
        "position_count": portfolio["position_count"],
        "cash": portfolio["cash"],
        "market_value": portfolio["market_value"],
        "equity": portfolio["equity"],
        "realized_pnl": portfolio["realized_pnl"],
        "unrealized_pnl": portfolio["unrealized_pnl"],
        "gross_exposure_pct": portfolio["gross_exposure_pct"],
        "symbol_exposures_pct": symbol_exposures,
        "risk_reasons": risk_reasons,
        "observed_at": now,
    }
    write_json(daily_report_path, daily_report)

    dashboard = {
        "stage": "V81.12",
        "portfolio_state": state,
        "position_count": portfolio["position_count"],
        "cash": portfolio["cash"],
        "market_value": portfolio["market_value"],
        "equity": portfolio["equity"],
        "realized_pnl": portfolio["realized_pnl"],
        "unrealized_pnl": portfolio["unrealized_pnl"],
        "gross_exposure_pct": portfolio["gross_exposure_pct"],
        "risk_reasons": risk_reasons,
        "read_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now,
    }
    write_json(dashboard_path, dashboard)

    recovery = {
        "stage": "V81.12",
        "portfolio_state_path": str(portfolio_state_path.resolve()),
        "processed_fill_count": len(processed),
        "last_equity": portfolio["equity"],
        "last_observed_at": now,
        "recovery_ready": not blocking,
        "shadow_only": True,
    }
    write_json(recovery_snapshot_path, recovery)

    result = {
        "stage_range": "V81.09-V81.12",
        "implementation_type": "SHADOW_PORTFOLIO_AND_PNL_ENGINE",
        "status": status,
        "state": state,
        "execution_ready": execution_ready,
        "new_fill_count": new_fill_count,
        "processed_fill_count": len(processed),
        "position_count": portfolio["position_count"],
        "cash": portfolio["cash"],
        "market_value": portfolio["market_value"],
        "equity": portfolio["equity"],
        "realized_pnl": portfolio["realized_pnl"],
        "unrealized_pnl": portfolio["unrealized_pnl"],
        "gross_exposure_pct": portfolio["gross_exposure_pct"],
        "risk_reasons": risk_reasons,
        "portfolio_state_written": True,
        "equity_history_written": True,
        "daily_report_written": True,
        "dashboard_state_written": True,
        "recovery_snapshot_written": True,
        "shadow_only": True,
        "paper_only": True,
        "read_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "cancel_enabled": False,
        "replace_enabled": False,
        "position_close_enabled": False,
        "live_trading_enabled": False,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "issue_count": len(issues),
        "blocking_issue_count": sum(
            1 for item in issues if item.get("blocking")
        ),
        "issues": issues,
        "next_phase": (
            "V82_01_AUTONOMOUS_SHADOW_TRADING"
            if state in {
                "SHADOW_PORTFOLIO_UPDATED",
                "SHADOW_PORTFOLIO_NO_CHANGE",
            }
            else "V81_09_TO_V81_12_WAIT_PORTFOLIO_GATE"
        ),
        "validation_mode": "LOCAL_SHADOW_PORTFOLIO_ONLY",
        "observed_at": now,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
