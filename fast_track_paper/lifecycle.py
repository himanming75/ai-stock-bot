from __future__ import annotations
from typing import Any

def process_tick(
    positions: list[dict[str, Any]],
    tick_prices: dict[str, float],
    policy: dict[str, Any],
) -> dict[str, Any]:
    stop_loss=float(policy.get("stop_loss_pct",3.0))/100.0
    take_profit=float(policy.get("take_profit_pct",5.0))/100.0
    trailing=float(policy.get("trailing_stop_pct",2.0))/100.0
    updated=[]
    exits=[]
    for source in positions:
        row=dict(source)
        symbol=str(row.get("symbol"))
        mark=float(tick_prices.get(symbol,row.get("average_cost",0.0)))
        cost=float(row.get("average_cost",0.0))
        highest=max(float(row.get("highest_price",cost)),mark)
        row["highest_price"]=highest
        pnl_pct=(mark-cost)/cost if cost else 0.0
        trail_drawdown=(mark-highest)/highest if highest else 0.0
        reason=None
        if pnl_pct<=-stop_loss:
            reason="STOP_LOSS"
        elif pnl_pct>=take_profit:
            reason="TAKE_PROFIT"
        elif highest>cost and trail_drawdown<=-trailing:
            reason="TRAILING_STOP"
        if reason:
            qty=int(row.get("quantity",0))
            realized=round((mark-cost)*qty,2)
            exits.append({
                "strategy_id":row.get("strategy_id"),
                "symbol":symbol,
                "quantity":qty,
                "exit_price":mark,
                "average_cost":cost,
                "realized_pnl":realized,
                "exit_reason":reason,
                "state":"CLOSED",
            })
            row["quantity"]=0
            row["state"]="CLOSED"
            row["realized_pnl"]=realized
            row["exit_reason"]=reason
        else:
            row["mark_price"]=mark
            row["market_value"]=round(int(row.get("quantity",0))*mark,2)
            row["unrealized_pnl"]=round(
                (mark-cost)*int(row.get("quantity",0)),2
            )
        updated.append(row)
    return {"positions":updated,"exits":exits}
