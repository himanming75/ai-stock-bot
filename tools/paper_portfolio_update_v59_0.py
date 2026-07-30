#!/usr/bin/env python3
"""V59.0 Paper Portfolio Update Integration Foundation.

Consumes a V57 execution result plus an existing paper account state and
deterministically updates cash, positions, realized/unrealized P&L, equity,
account snapshot, audit trail, and SHA-256 ledger. Offline only.
"""
from __future__ import annotations
import argparse, hashlib, json
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Sequence

VERSION="59.0"
MONEY_Q=Decimal("0.0001")
QTY_Q=Decimal("0.000001")
RATIO_Q=Decimal("0.000001")

def canonical_hash(x:Any)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def dec(x:Any,field:str)->Decimal:
    try: v=Decimal(str(x))
    except (InvalidOperation,ValueError) as e: raise ValueError(f"{field} must be numeric") from e
    if not v.is_finite(): raise ValueError(f"{field} must be finite")
    return v

def money(x:Decimal)->str: return format(x.quantize(MONEY_Q,rounding=ROUND_HALF_UP),"f")
def qty(x:Decimal)->str:
    s=format(x.quantize(QTY_Q,rounding=ROUND_HALF_UP),"f").rstrip("0").rstrip(".")
    return s or "0"
def ratio(x:Decimal)->str: return format(x.quantize(RATIO_Q,rounding=ROUND_HALF_UP),"f")

def load_json(path:Path)->dict[str,Any]:
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError("input must be a JSON object")
    return x

def unwrap(x:dict[str,Any])->dict[str,Any]:
    y=x.get("result",x)
    if not isinstance(y,dict): raise ValueError("result must be an object")
    return y

def iso_utc(x:str)->str:
    try: d=datetime.fromisoformat(x.replace("Z","+00:00"))
    except ValueError as e: raise ValueError("snapshot_time must be ISO-8601") from e
    if d.tzinfo is None: raise ValueError("snapshot_time must include timezone")
    return d.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

class PaperPortfolioUpdateV590:
    def __init__(self,*,mode:str="paper",enable_live:bool=False,allow_short:bool=False):
        if mode not in {"replay","paper","live"}: raise ValueError("mode must be replay, paper, or live")
        self.mode=mode; self.enable_live=enable_live; self.allow_short=allow_short

    def _gate(self):
        if self.mode=="live":
            if not self.enable_live: raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError("live portfolio transport is intentionally not implemented in V59.0")

    def update(self,execution_raw:dict[str,Any],state_raw:dict[str,Any],*,market_prices:dict[str,Any],snapshot_time:str)->dict[str,Any]:
        self._gate()
        execution=unwrap(execution_raw); state=deepcopy(unwrap(state_raw))
        if execution.get("network_used") or state.get("network_used"): raise ValueError("network_used must be false")
        if execution.get("status")!="PASS": raise ValueError("execution status must be PASS")
        if execution.get("final_state") not in {"FILLED","PARTIALLY_FILLED"}: raise ValueError("execution must contain a fill")

        symbol=str(execution.get("symbol","")).strip().upper()
        action=str(execution.get("action","")).strip().upper()
        if not symbol: raise ValueError("symbol is required")
        if action not in {"BUY","SELL"}: raise ValueError("action must be BUY or SELL")
        fill_qty=dec(execution.get("filled_quantity"),"filled_quantity")
        fill_price=dec(execution.get("average_fill_price"),"average_fill_price")
        if fill_qty<=0 or fill_price<=0: raise ValueError("fill quantity and price must be positive")

        starting_cash=dec(state.get("cash","0"),"cash")
        initial_equity=dec(state.get("initial_equity",state.get("equity",starting_cash)),"initial_equity")
        prior_equity=dec(state.get("equity",initial_equity),"equity")
        commission=dec(state.get("commission_per_trade","0"),"commission_per_trade")
        if commission<0: raise ValueError("commission_per_trade must be non-negative")

        positions={}
        for p in state.get("positions",[]):
            s=str(p.get("symbol","")).upper()
            if not s or s in positions: raise ValueError("invalid or duplicate position symbol")
            positions[s]={
                "symbol":s,
                "quantity":dec(p.get("quantity"),"position quantity"),
                "average_cost":dec(p.get("average_cost"),"average_cost"),
                "realized_pnl":dec(p.get("realized_pnl","0"),"realized_pnl"),
                "total_commission":dec(p.get("total_commission","0"),"total_commission"),
            }

        before=deepcopy(positions.get(symbol,{"symbol":symbol,"quantity":Decimal("0"),"average_cost":Decimal("0"),"realized_pnl":Decimal("0"),"total_commission":Decimal("0")}))
        p=deepcopy(before)
        gross=fill_qty*fill_price
        realized_delta=Decimal("0")
        cash=starting_cash

        if action=="BUY":
            if cash < gross+commission: raise ValueError("insufficient cash")
            new_qty=p["quantity"]+fill_qty
            if p["quantity"]<0:
                raise ValueError("buy-to-cover is not supported in V59.0")
            p["average_cost"]=((p["quantity"]*p["average_cost"])+gross+commission)/new_qty
            p["quantity"]=new_qty; cash-=gross+commission
            event="POSITION_OPENED" if before["quantity"]==0 else "POSITION_INCREASED"
        else:
            if p["quantity"]<=0:
                if not self.allow_short: raise ValueError("cannot sell without a long position")
                raise NotImplementedError("short opening is intentionally not implemented in V59.0")
            if fill_qty>p["quantity"]: raise ValueError("sell quantity exceeds position")
            realized_delta=(fill_price-p["average_cost"])*fill_qty-commission
            p["realized_pnl"]+=realized_delta
            p["quantity"]-=fill_qty; p["total_commission"]+=commission
            cash+=gross-commission
            event="POSITION_CLOSED" if p["quantity"]==0 else "POSITION_REDUCED"
            if p["quantity"]==0: p["average_cost"]=Decimal("0")

        if action=="BUY": p["total_commission"]+=commission
        if p["quantity"]==0:
            positions.pop(symbol,None)
        else:
            positions[symbol]=p

        rendered=[]; total_mv=total_cost=total_unreal=total_realized=total_comm=Decimal("0")
        for s in sorted(positions):
            x=positions[s]
            if s not in market_prices: raise ValueError(f"missing market price for {s}")
            mp=dec(market_prices[s],f"market price {s}")
            if mp<0: raise ValueError("market price must be non-negative")
            mv=x["quantity"]*mp; cost=x["quantity"]*x["average_cost"]; unreal=mv-cost
            core={"symbol":s,"quantity":qty(x["quantity"]),"average_cost":money(x["average_cost"]),"market_price":money(mp),
                  "market_value":money(mv),"cost_basis":money(cost),"unrealized_pnl":money(unreal),
                  "realized_pnl":money(x["realized_pnl"]),"total_commission":money(x["total_commission"])}
            rendered.append({**core,"position_sha256":canonical_hash(core)})
            total_mv+=mv; total_cost+=cost; total_unreal+=unreal; total_realized+=x["realized_pnl"]; total_comm+=x["total_commission"]

        equity=cash+total_mv
        ledger_payload={"event_type":event,"symbol":symbol,"action":action,"quantity":qty(fill_qty),"price":money(fill_price),
                        "commission":money(commission),"cash_before":money(starting_cash),"cash_after":money(cash),
                        "position_quantity_before":qty(before["quantity"]),"position_quantity_after":qty(p["quantity"]),
                        "realized_pnl_delta":money(realized_delta),"execution_sha256":execution.get("execution_sha256")}
        ledger_core={**ledger_payload,"sequence":1,"previous_entry_sha256":"GENESIS","payload_sha256":canonical_hash(ledger_payload)}
        ledger=[{**ledger_core,"entry_sha256":canonical_hash(ledger_core)}]

        rec_core={"schema_version":"v59.0.paper_portfolio_update.1","version":VERSION,"status":"PASS","decision":"portfolio_updated",
                  "execution_sha256":execution.get("execution_sha256"),"starting_cash":money(starting_cash),"ending_cash":money(cash),
                  "total_market_value":money(total_mv),"total_cost_basis":money(total_cost),"total_realized_pnl":money(total_realized),
                  "total_unrealized_pnl":money(total_unreal),"total_commission":money(total_comm),"total_equity":money(equity),
                  "position_count":len(rendered),"positions":rendered,"ledger":ledger,"rejection_reasons":[],"network_used":False}
        reconciliation_sha=canonical_hash(rec_core)
        reconciliation={**rec_core,"reconciliation_sha256":reconciliation_sha}

        snap_time=iso_utc(snapshot_time)
        daily_pnl=equity-prior_equity; cumulative_pnl=equity-initial_equity
        zero=Decimal("0")
        snapshot_positions=[]
        for p0 in rendered:
            mv=dec(p0["market_value"],"market_value")
            alloc=mv/equity if equity else zero
            core={"symbol":p0["symbol"],"quantity":p0["quantity"],"market_value":p0["market_value"],
                  "allocation":ratio(alloc),"gross_exposure_contribution":ratio(abs(mv)/equity if equity else zero),
                  "net_exposure_contribution":ratio(mv/equity if equity else zero),
                  "unrealized_pnl":p0["unrealized_pnl"],"realized_pnl":p0["realized_pnl"]}
            snapshot_positions.append({**core,"allocation_sha256":canonical_hash(core)})
        snapshot_core={"schema_version":"v59.0.paper_account_snapshot.1","version":VERSION,"status":"PASS","decision":"snapshot",
                       "snapshot_time":snap_time,"reconciliation_sha256":reconciliation_sha,"cash_balance":money(cash),
                       "buying_power":money(cash),"total_market_value":money(total_mv),"net_liquidation_value":money(equity),
                       "prior_net_liquidation_value":money(prior_equity),"daily_pnl":money(daily_pnl),
                       "daily_return":ratio(daily_pnl/prior_equity if prior_equity else zero),"cumulative_pnl":money(cumulative_pnl),
                       "cumulative_return":ratio(cumulative_pnl/initial_equity if initial_equity else zero),
                       "cash_allocation":ratio(cash/equity if equity else zero),"invested_allocation":ratio(total_mv/equity if equity else zero),
                       "gross_exposure":ratio(abs(total_mv)/equity if equity else zero),"net_exposure":ratio(total_mv/equity if equity else zero),
                       "leverage_ratio":ratio(abs(total_mv)/equity if equity else zero),"long_market_value":money(total_mv),
                       "short_market_value":money(zero),"position_count":len(rendered),"positions":snapshot_positions,
                       "rejection_reasons":[],"network_used":False}
        snapshot={**snapshot_core,"snapshot_sha256":canonical_hash(snapshot_core)}

        final_core={"schema_version":"v59.0.paper_portfolio_update_integration.1","version":VERSION,"status":"PASS",
                    "decision":"portfolio_and_snapshot_updated","execution_sha256":execution.get("execution_sha256"),
                    "reconciliation":reconciliation,"snapshot":snapshot,"network_used":False}
        return {**final_core,"integration_sha256":canonical_hash(final_core)}

def parse_prices(text:str)->dict[str,str]:
    out={}
    for item in text.split(","):
        if not item.strip(): continue
        if "=" not in item: raise ValueError("market prices must use SYMBOL=PRICE")
        s,p=item.split("=",1); s=s.strip().upper()
        if not s or s in out: raise ValueError("invalid or duplicate market-price symbol")
        out[s]=p.strip()
    if not out: raise ValueError("at least one market price is required")
    return out

def parser():
    p=argparse.ArgumentParser(description="V59.0 Paper Portfolio Update Integration")
    p.add_argument("--execution",required=True); p.add_argument("--state",required=True)
    p.add_argument("--market-prices",required=True); p.add_argument("--snapshot-time",required=True)
    p.add_argument("--mode",choices=["replay","paper","live"],default="paper")
    p.add_argument("--enable-live",action="store_true"); p.add_argument("--allow-short",action="store_true")
    p.add_argument("--output",required=True); return p

def main(argv:Sequence[str]|None=None)->int:
    a=parser().parse_args(argv); output=Path(a.output)
    try:
        result=PaperPortfolioUpdateV590(mode=a.mode,enable_live=a.enable_live,allow_short=a.allow_short).update(
            load_json(Path(a.execution)),load_json(Path(a.state)),market_prices=parse_prices(a.market_prices),snapshot_time=a.snapshot_time)
        output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
        print(json.dumps(result,indent=2,sort_keys=True)); return 0
    except (OSError,ValueError,PermissionError,NotImplementedError,TypeError,json.JSONDecodeError) as e:
        err={"schema_version":"v59.0.paper_portfolio_update_error.1","version":VERSION,"status":"FAIL","error":str(e),"network_used":False}
        output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(err,indent=2,sort_keys=True),encoding="utf-8")
        print(json.dumps(err,indent=2,sort_keys=True)); return 1
if __name__=="__main__": raise SystemExit(main())
