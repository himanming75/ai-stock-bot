from __future__ import annotations
from typing import Any

def daily_close(
    starting_cash: float,
    positions: list[dict[str, Any]],
    fills: list[dict[str, Any]],
    exits: list[dict[str, Any]],
    closing_prices: dict[str, float],
) -> dict[str, Any]:
    buy_cost=sum(float(row.get("fill_notional",0.0)) for row in fills)
    sale_proceeds=sum(
        int(row.get("quantity",0))*float(row.get("exit_price",0.0))
        for row in exits
    )
    ending_cash=round(starting_cash-buy_cost+sale_proceeds,2)
    open_value=0.0
    unrealized=0.0
    realized=sum(float(row.get("realized_pnl",0.0)) for row in exits)
    open_positions=[]
    for row in positions:
        if row.get("state")=="CLOSED" or int(row.get("quantity",0))<=0:
            continue
        mark=float(closing_prices.get(
            str(row.get("symbol")),
            row.get("mark_price",row.get("average_cost",0.0)),
        ))
        qty=int(row.get("quantity",0))
        cost=float(row.get("average_cost",0.0))
        value=round(qty*mark,2)
        pnl=round((mark-cost)*qty,2)
        item=dict(row)
        item["mark_price"]=mark
        item["market_value"]=value
        item["unrealized_pnl"]=pnl
        open_positions.append(item)
        open_value+=value
        unrealized+=pnl
    ending_equity=round(ending_cash+open_value,2)
    return {
        "starting_cash":round(starting_cash,2),
        "ending_cash":ending_cash,
        "open_market_value":round(open_value,2),
        "ending_equity":ending_equity,
        "realized_pnl":round(realized,2),
        "unrealized_pnl":round(unrealized,2),
        "total_pnl":round(realized+unrealized,2),
        "open_positions":open_positions,
        "closed_position_count":len(exits),
    }
