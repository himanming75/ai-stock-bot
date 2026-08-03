from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from portfolio_rebalance.io import (
    load_json,
    load_jsonl,
    write_json,
    append_jsonl,
    digest,
)
from portfolio_rebalance.models import (
    target_weights,
    current_weights,
    merge_weight_rows,
)
from portfolio_rebalance.mapping import (
    build_strategy_positions,
    strategy_symbol_map,
)
from portfolio_rebalance.planner import build_trade_intents
from portfolio_rebalance.turnover import apply_turnover_limit
from portfolio_rebalance.dedup import deduplicate_intents
from portfolio_rebalance.risk import evaluate_rebalance_risk

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v99_33_to_v99_64/input/rebalance_policy.json"
    )
    portfolio = load_json(
        root / "release/v99_01_to_v99_32/actual/"
        "ai_portfolio_manager_result.json"
    )
    account = load_json(
        root / "release/v96_01_to_v96_32/actual/"
        "paper_account_reconciliation_result.json"
    )
    references = load_json(
        root / "release/v99_33_to_v99_64/input/reference_prices.json"
    )
    ledger_path = (
        root / "release/v99_33_to_v99_64/actual/"
        "portfolio_trade_intent_ledger.jsonl"
    )

    if portfolio.get("state") != "AI_PORTFOLIO_MANAGER_READY":
        return {
            "stage": "V99.64",
            "stage_range": "V99.33-V99.64",
            "state": "PORTFOLIO_REBALANCE_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    cash = float(
        account.get("cash_reconciliation", {}).get(
            "reported_ending_cash", 0.0
        )
    )
    equity = float(
        account.get("equity_reconciliation", {}).get(
            "reported_equity", 0.0
        )
    )
    positions = build_strategy_positions(account, portfolio, policy)
    targets = target_weights(portfolio)
    currents = current_weights(equity, cash, positions)
    weights = merge_weight_rows(targets, currents)
    symbol_map = strategy_symbol_map(policy)

    planned = build_trade_intents(
        weights,
        equity,
        symbol_map,
        references,
        policy,
    )
    turnover = apply_turnover_limit(planned, equity, cash, policy)
    dedup = deduplicate_intents(
        turnover["intents"],
        load_jsonl(ledger_path),
    )
    unique = dedup["unique_intents"]
    risk = evaluate_rebalance_risk(
        unique,
        float(targets.get("CASH", 0.0)),
        equity,
        cash,
        policy,
    )

    actionable = [
        row for row in unique
        if float(row.get("planned_notional", 0.0)) > 0
    ]
    state = (
        "PORTFOLIO_REBALANCE_INTENTS_READY"
        if risk["passed"] and actionable
        else (
            "PORTFOLIO_REBALANCE_NO_ACTION"
            if risk["passed"]
            else "PORTFOLIO_REBALANCE_REVIEW_REQUIRED"
        )
    )

    observed = datetime.now(timezone.utc).isoformat()
    body = {
        "stage": "V99.64",
        "stage_range": "V99.33-V99.64",
        "state": state,
        "status": "PASS",
        "observed_at": observed,
        "rebalance_id": digest({
            "portfolio_id": portfolio.get("portfolio_id"),
            "weights": weights,
            "policy": policy,
        })[:24],
        "source_portfolio_id": portfolio.get("portfolio_id"),
        "account_equity": round(equity, 6),
        "account_cash": round(cash, 6),
        "target_weights": targets,
        "current_weights": currents,
        "weight_comparison": weights,
        "strategy_positions": positions,
        "planned_intent_count": len(planned),
        "turnover": turnover,
        "unique_intents": unique,
        "duplicate_intents": dedup["duplicate_intents"],
        "duplicate_intent_count": dedup["duplicate_count"],
        "actionable_intent_count": len(actionable),
        "risk": risk,
        "execution_authorized": False,
        "manual_approval_required": True,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "next_phase": "V100_01_AI_RISK_MANAGER_CORE",
    }
    body["portfolio_rebalance_certificate_sha256"] = digest(body)

    write_json(
        root / "release/v99_33_to_v99_64/actual/"
        "portfolio_rebalance_result.json",
        body,
    )
    for row in unique:
        append_jsonl(ledger_path, {
            "observed_at": observed,
            "rebalance_id": body["rebalance_id"],
            "intent_key": row.get("intent_key"),
            "strategy_id": row.get("strategy_id"),
            "symbol": row.get("symbol"),
            "side": row.get("side"),
            "planned_notional": row.get("planned_notional"),
            "quantity": row.get("quantity"),
            "state": row.get("state"),
            "submission_allowed": False,
        })
    return body
