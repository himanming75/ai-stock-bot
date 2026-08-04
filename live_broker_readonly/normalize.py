from __future__ import annotations
from typing import Any

def normalize_account(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "account_id_masked":str(value.get("account_id_masked","UNKNOWN")),
        "status":str(value.get("status","UNKNOWN")).upper(),
        "currency":str(value.get("currency","USD")).upper(),
        "cash":round(float(value.get("cash",0.0)),2),
        "buying_power":round(float(value.get("buying_power",0.0)),2),
        "equity":round(float(value.get("equity",0.0)),2),
        "day_trade_count":int(value.get("day_trade_count",0)),
    }

def normalize_positions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output=[]
    for row in rows:
        quantity=float(row.get("quantity",0.0))
        average_cost=float(row.get("average_cost",0.0))
        market_price=float(row.get("market_price",average_cost))
        output.append({
            "symbol":str(row.get("symbol","")).upper(),
            "quantity":quantity,
            "average_cost":round(average_cost,4),
            "market_price":round(market_price,4),
            "market_value":round(quantity*market_price,2),
            "unrealized_pnl":round(
                quantity*(market_price-average_cost),2
            ),
            "side":"LONG" if quantity>=0 else "SHORT",
        })
    output.sort(key=lambda item:item["symbol"])
    return output

def normalize_orders(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output=[]
    for row in rows:
        output.append({
            "broker_order_id_masked":str(
                row.get("broker_order_id_masked","UNKNOWN")
            ),
            "symbol":str(row.get("symbol","")).upper(),
            "side":str(row.get("side","UNKNOWN")).upper(),
            "quantity":float(row.get("quantity",0.0)),
            "filled_quantity":float(row.get("filled_quantity",0.0)),
            "order_type":str(row.get("order_type","UNKNOWN")).upper(),
            "status":str(row.get("status","UNKNOWN")).upper(),
        })
    return output
