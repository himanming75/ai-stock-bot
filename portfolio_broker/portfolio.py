from __future__ import annotations
from collections import defaultdict
from typing import Any
from portfolio_broker.models import account_dict,position_dict

def aggregate(adapters:list)->dict[str,Any]:
    accounts=[];positions=[];orders=[]
    for adapter in adapters:
        accounts.append(account_dict(adapter.account()))
        positions.extend(position_dict(x) for x in adapter.positions())
        orders.extend({"broker_id":adapter.broker_id,**x} for x in adapter.orders())
    total_equity=sum(float(x["equity"]) for x in accounts)
    total_cash=sum(float(x["cash"]) for x in accounts)
    gross_exposure=sum(abs(float(x["market_value"])) for x in positions)
    net_exposure=sum(float(x["market_value"]) for x in positions)
    symbol_values=defaultdict(float)
    strategy_values=defaultdict(float)
    broker_values=defaultdict(float)
    for p in positions:
        value=float(p["market_value"])
        symbol_values[p["symbol"]]+=value
        strategy_values[p["strategy_id"]]+=value
        broker_values[p["broker_id"]]+=value
    def weights(values):
        denom=total_equity or 1.0
        return [
            {"name":name,"market_value":round(value,2),"weight_pct":round(value/denom*100,4)}
            for name,value in sorted(values.items())
        ]
    return {
        "accounts":accounts,
        "positions":positions,
        "orders":orders,
        "summary":{
            "account_count":len(accounts),
            "position_count":len(positions),
            "total_equity":round(total_equity,2),
            "total_cash":round(total_cash,2),
            "cash_weight_pct":round(total_cash/(total_equity or 1)*100,4),
            "gross_exposure":round(gross_exposure,2),
            "gross_exposure_pct":round(gross_exposure/(total_equity or 1)*100,4),
            "net_exposure":round(net_exposure,2),
            "net_exposure_pct":round(net_exposure/(total_equity or 1)*100,4),
        },
        "symbol_allocation":weights(symbol_values),
        "strategy_allocation":weights(strategy_values),
        "broker_allocation":weights(broker_values),
    }
