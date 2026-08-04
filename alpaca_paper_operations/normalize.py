from __future__ import annotations
from typing import Any

def f(value:Any,default:float=0.0)->float:
    try:return float(value)
    except Exception:return default

def normalize_account(v:dict[str,Any])->dict[str,Any]:
    return {
        "account_id_masked":"****"+str(v.get("id",""))[-4:],
        "status":v.get("status"),
        "currency":v.get("currency","USD"),
        "cash":round(f(v.get("cash")),2),
        "buying_power":round(f(v.get("buying_power")),2),
        "equity":round(f(v.get("equity")),2),
        "last_equity":round(f(v.get("last_equity")),2),
        "trading_blocked":bool(v.get("trading_blocked",False)),
        "account_blocked":bool(v.get("account_blocked",False)),
        "pattern_day_trader":bool(v.get("pattern_day_trader",False)),
    }

def normalize_positions(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    out=[]
    for v in rows:
        out.append({
            "symbol":str(v.get("symbol","")).upper(),
            "quantity":f(v.get("qty")),
            "side":v.get("side"),
            "average_entry_price":round(f(v.get("avg_entry_price")),4),
            "market_value":round(f(v.get("market_value")),2),
            "cost_basis":round(f(v.get("cost_basis")),2),
            "unrealized_pnl":round(f(v.get("unrealized_pl")),2),
            "unrealized_pnl_pct":round(f(v.get("unrealized_plpc"))*100,6),
            "current_price":round(f(v.get("current_price")),4),
        })
    return out

def normalize_orders(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    out=[]
    for v in rows:
        out.append({
            "order_id":v.get("id"),
            "client_order_id":v.get("client_order_id"),
            "symbol":str(v.get("symbol","")).upper(),
            "quantity":f(v.get("qty")),
            "filled_quantity":f(v.get("filled_qty")),
            "side":v.get("side"),
            "order_type":v.get("type"),
            "time_in_force":v.get("time_in_force"),
            "status":v.get("status"),
            "submitted_at":v.get("submitted_at"),
            "filled_at":v.get("filled_at"),
            "average_fill_price":(
                round(f(v.get("filled_avg_price")),4)
                if v.get("filled_avg_price") is not None else None
            ),
        })
    return out
