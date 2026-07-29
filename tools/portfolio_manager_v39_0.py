from __future__ import annotations
import argparse, hashlib, json, uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence

VERSION = "39.0"

def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def canonical_hash(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def dec(value,name):
    try: n=Decimal(str(value))
    except (InvalidOperation,ValueError) as e: raise ValueError(f"{name} must be numeric") from e
    if not n.is_finite(): raise ValueError(f"{name} must be finite")
    return n

def pos(value,name):
    n=dec(value,name)
    if n<=0: raise ValueError(f"{name} must be greater than zero")
    return n

def nonneg(value,name):
    n=dec(value,name)
    if n<0: raise ValueError(f"{name} must be zero or greater")
    return n

def norm(n):
    return "0" if n==0 else format(n.normalize(),"f")

@dataclass(frozen=True)
class PortfolioPosition:
    symbol:str; side:str; quantity:str; average_price:str; market_price:str
    market_value:str; cost_basis:str; unrealized_pnl:str; realized_pnl:str; weight_pct:str

@dataclass(frozen=True)
class PortfolioEvent:
    event_id:str; generated_at:str; event_type:str; symbol:str|None
    message:str; details:dict[str,Any]; event_sha256:str

@dataclass(frozen=True)
class PortfolioSnapshot:
    portfolio_id:str; cash:str; market_value:str; equity:str; buying_power:str
    gross_exposure:str; gross_exposure_pct:str; realized_pnl:str; unrealized_pnl:str
    total_pnl:str; position_count:int; positions:list[PortfolioPosition]
    event_count:int; generated_at:str; snapshot_sha256:str

class PortfolioManager:
    def __init__(self, *, starting_cash:str, buying_power_multiplier:str="1"):
        self.portfolio_id=f"portfolio-{uuid.uuid4().hex}"
        self.cash=nonneg(starting_cash,"starting_cash")
        self.mult=pos(buying_power_multiplier,"buying_power_multiplier")
        self._positions={}
        self._events=[]
        self._record("portfolio_created",None,"Portfolio created.",
                     {"starting_cash":norm(self.cash),"buying_power_multiplier":norm(self.mult)})

    def _record(self,event_type,symbol,message,details):
        core={"event_id":f"evt-{uuid.uuid4().hex}","generated_at":utc_now(),
              "event_type":event_type,"symbol":symbol,"message":message,"details":details}
        ev=PortfolioEvent(**core,event_sha256=canonical_hash(core)); self._events.append(ev); return ev

    def upsert_position(self, *, symbol, side, quantity, average_price, market_price, realized_pnl="0"):
        symbol=symbol.strip().upper(); side=side.strip().lower()
        if not symbol: raise ValueError("symbol is required")
        if side not in {"long","short"}: raise ValueError("side must be long or short")
        q=pos(quantity,"quantity"); a=pos(average_price,"average_price"); m=pos(market_price,"market_price")
        r=dec(realized_pnl,"realized_pnl")
        self._positions[symbol]={"symbol":symbol,"side":side,"quantity":q,
          "average_price":a,"market_price":m,"realized_pnl":r}
        return self._record("position_upserted",symbol,"Portfolio position added or updated.",
          {"side":side,"quantity":norm(q),"average_price":norm(a),"market_price":norm(m),"realized_pnl":norm(r)})

    def remove_position(self,symbol):
        symbol=symbol.strip().upper()
        if symbol not in self._positions: raise KeyError(f"Unknown position: {symbol}")
        del self._positions[symbol]
        return self._record("position_removed",symbol,"Portfolio position removed.",{})

    def adjust_cash(self,amount,reason):
        d=dec(amount,"amount")
        if self.cash+d<0: raise ValueError("cash adjustment would make cash negative")
        self.cash+=d
        return self._record("cash_adjusted",None,reason,{"delta":norm(d),"cash":norm(self.cash)})

    def market_value(self):
        return sum((p["quantity"]*p["market_price"] for p in self._positions.values()),Decimal("0"))

    def realized_pnl(self):
        return sum((p["realized_pnl"] for p in self._positions.values()),Decimal("0"))

    def unrealized_pnl(self):
        total=Decimal("0")
        for p in self._positions.values():
            q,a,m=p["quantity"],p["average_price"],p["market_price"]
            total += (m-a)*q if p["side"]=="long" else (a-m)*q
        return total

    def equity(self): return self.cash+self.market_value()
    def buying_power(self): return self.cash + self.equity()*(self.mult-Decimal("1"))

    def snapshot(self):
        eq=self.equity(); mv=self.market_value(); realized=self.realized_pnl(); unreal=self.unrealized_pnl()
        positions=[]
        for p in sorted(self._positions.values(),key=lambda x:x["symbol"]):
            q,a,m=p["quantity"],p["average_price"],p["market_price"]
            pv=q*m; cb=q*a; up=(m-a)*q if p["side"]=="long" else (a-m)*q
            weight=(pv/eq*Decimal("100")) if eq>0 else Decimal("0")
            positions.append(PortfolioPosition(p["symbol"],p["side"],norm(q),norm(a),norm(m),
                norm(pv),norm(cb),norm(up),norm(p["realized_pnl"]),norm(weight)))
        core={"portfolio_id":self.portfolio_id,"cash":norm(self.cash),"market_value":norm(mv),
          "equity":norm(eq),"buying_power":norm(self.buying_power()),"gross_exposure":norm(mv),
          "gross_exposure_pct":norm(mv/eq*Decimal("100") if eq>0 else Decimal("0")),
          "realized_pnl":norm(realized),"unrealized_pnl":norm(unreal),"total_pnl":norm(realized+unreal),
          "position_count":len(positions),"positions":positions,"event_count":len(self._events),
          "generated_at":utc_now()}
        return PortfolioSnapshot(**core,snapshot_sha256=canonical_hash({**core,"positions":[asdict(x) for x in positions]}))

    def ledger(self): return list(self._events)
    def export(self):
        return {"schema_version":"v39.0.portfolio_ledger.1","version":VERSION,
                "snapshot":asdict(self.snapshot()),"events":[asdict(x) for x in self.ledger()],
                "network_used":False}

def parse_position_spec(spec):
    parts=spec.split(":")
    if len(parts) not in {4,5,6}: raise ValueError("position format must be SYMBOL:QTY:AVG:MARKET[:SIDE][:REALIZED_PNL]")
    return {"symbol":parts[0],"quantity":parts[1],"average_price":parts[2],"market_price":parts[3],
            "side":parts[4] if len(parts)>=5 else "long","realized_pnl":parts[5] if len(parts)>=6 else "0"}

def main(argv:Sequence[str]|None=None):
    p=argparse.ArgumentParser(description="V39.0 Portfolio Manager Foundation")
    p.add_argument("--cash",default="100000"); p.add_argument("--buying-power-multiplier",default="1")
    p.add_argument("--position",action="append",default=[])
    p.add_argument("--output",default="release/v39/audit/portfolio_manager_result_v39_0.json")
    a=p.parse_args(argv)
    specs=a.position or ["AAPL:100:200:212","MSFT:50:350:360","NVDA:20:900:925"]
    manager=PortfolioManager(starting_cash=a.cash,buying_power_multiplier=a.buying_power_multiplier)
    for spec in specs: manager.upsert_position(**parse_position_spec(spec))
    payload=manager.export()
    path=Path(a.output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2,sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())
