from __future__ import annotations
from typing import Any

def normalize_account(v:dict[str,Any])->dict[str,Any]:
    def f(x):
        try:return float(x)
        except Exception:return 0.0
    return {
        "account_id_masked":"****"+str(v.get("id",""))[-4:],
        "status":v.get("status","UNKNOWN"),
        "cash":round(f(v.get("cash")),2),
        "equity":round(f(v.get("equity")),2),
        "buying_power":round(f(v.get("buying_power")),2),
        "trading_blocked":bool(v.get("trading_blocked",False)),
        "account_blocked":bool(v.get("account_blocked",False)),
    }

def normalize_positions(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    out=[]
    for v in rows:
        try: qty=float(v.get("qty",0))
        except Exception: qty=0.0
        out.append({
            "symbol":str(v.get("symbol","")).upper(),
            "quantity":qty,
            "side":v.get("side"),
            "market_value":float(v.get("market_value",0) or 0),
        })
    return out

def normalize_orders(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    return [{
        "id":v.get("id"),
        "symbol":str(v.get("symbol","")).upper(),
        "side":v.get("side"),
        "status":v.get("status"),
        "qty":float(v.get("qty",0) or 0),
    } for v in rows]
