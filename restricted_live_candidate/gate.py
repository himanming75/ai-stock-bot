from __future__ import annotations
from typing import Any

OPEN_STATUSES={"new","accepted","pending_new","partially_filled"}

def evaluate(
    candidates:list[dict[str,Any]],
    account:dict[str,Any],
    positions:list[dict[str,Any]],
    orders:list[dict[str,Any]],
    policy:dict[str,Any],
)->dict[str,Any]:
    position_symbols={p.get("symbol") for p in positions if p.get("quantity")}
    open_order_symbols={
        o.get("symbol") for o in orders
        if str(o.get("status","")).lower() in OPEN_STATUSES
    }
    rows=[]
    for c in candidates:
        symbol=c.get("symbol")
        checks={
            "account_active":account.get("status")=="ACTIVE",
            "account_not_blocked":not account.get("account_blocked"),
            "trading_not_blocked":not account.get("trading_blocked"),
            "symbol_allowed":symbol in set(policy.get("allowed_symbols",[])),
            "quantity_within_limit":c.get("quantity",0)<=float(policy.get("maximum_quantity",1)),
            "notional_within_limit":c.get("estimated_notional",0)<=float(policy.get("maximum_notional",100)),
            "no_existing_position_conflict":symbol not in position_symbols,
            "no_open_order_conflict":symbol not in open_order_symbols,
            "daily_loss_clear":float(policy.get("current_daily_pnl",0))>-abs(float(policy.get("maximum_daily_loss",20))),
            "daily_order_count_clear":int(policy.get("current_daily_order_count",0))<int(policy.get("maximum_daily_orders",1)),
            "kill_switch_clear":policy.get("kill_switch_clear") is True,
            "paper_qualification_passed":policy.get("paper_qualification_passed") is True,
        }
        failed=[k for k,v in checks.items() if not v]
        rows.append({
            "candidate_id":c.get("candidate_id"),
            "passed":not failed,
            "checks":checks,
            "failed":failed,
        })
    return {
        "rows":rows,
        "passed":bool(rows) and all(r["passed"] for r in rows),
        "eligible_count":sum(1 for r in rows if r["passed"]),
        "ineligible_count":sum(1 for r in rows if not r["passed"]),
    }
