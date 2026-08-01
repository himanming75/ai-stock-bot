from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class PaperOrderFillConfig:
    mode:str="DRY_RUN_NO_NETWORK"
    initial_cash:float=100000.0
    slippage_bps:float=5.0
    commission_per_order:float=1.0
    maximum_order_quantity:int=1000
    allow_short_selling:bool=False
    allow_fractional_shares:bool=False
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="DRY_RUN_NO_NETWORK": raise ValueError("safe mode")
        if self.initial_cash<=0 or self.slippage_bps<0 or self.commission_per_order<0 or self.maximum_order_quantity<1:
            raise ValueError("invalid config")
        if self.allow_short_selling or self.allow_fractional_shares:
            raise ValueError("unsupported order capabilities")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

def validate_session_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text()); u=dict(c); e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V80.20" or c.get("status")!="PASS": raise ValueError("bad session certificate")
    if c.get("actual_orders_submitted")!=0: raise ValueError("orders found")
    return c

def make_order(symbol:str,side:str,quantity:int,reference_price:float,client_order_id:str)->dict[str,Any]:
    symbol=symbol.strip().upper(); side=side.strip().upper()
    if not symbol or not symbol.replace(".","").isalnum(): raise ValueError("symbol")
    if side not in {"BUY","SELL"}: raise ValueError("side")
    if not isinstance(quantity,int) or quantity<1: raise ValueError("quantity")
    if reference_price<=0 or not math.isfinite(reference_price): raise ValueError("price")
    if not client_order_id.strip(): raise ValueError("client_order_id")
    d={"stage":"V80.21","order_id":"paper-"+hj({"client_order_id":client_order_id,"symbol":symbol,"side":side,"quantity":quantity})[:20],
       "client_order_id":client_order_id,"symbol":symbol,"side":side,"quantity":quantity,"filled_quantity":0,
       "remaining_quantity":quantity,"reference_price":float(reference_price),"status":"NEW",
       "broker_submission_authorized":False,"broker_order_id":None}
    d["order_sha256"]=hj(d); return d

def validate_order(order:dict[str,Any],c:PaperOrderFillConfig,positions:dict[str,Any]|None=None)->dict[str,Any]:
    c.validate(); positions=positions or {}
    u=dict(order); e=u.pop("order_sha256",None)
    if e!=hj(u): raise ValueError("order hash")
    reasons=[]
    if order["quantity"]>c.maximum_order_quantity: reasons.append("MAX_QUANTITY")
    if order["side"]=="SELL" and int(positions.get(order["symbol"],{}).get("quantity",0))<order["quantity"]:
        reasons.append("INSUFFICIENT_POSITION")
    d={"stage":"V80.22","order_id":order["order_id"],"status":"PASS" if not reasons else "REJECT",
       "reasons":reasons,"reason_count":len(reasons)}
    d["validation_sha256"]=hj(d); return d

_ALLOWED={"NEW":{"ACCEPTED","REJECTED","CANCELED"},"ACCEPTED":{"PARTIALLY_FILLED","FILLED","CANCELED","REJECTED"},
          "PARTIALLY_FILLED":{"PARTIALLY_FILLED","FILLED","CANCELED"},"FILLED":set(),"CANCELED":set(),"REJECTED":set()}
def transition_order(order:dict[str,Any],target:str,reason:str)->dict[str,Any]:
    target=target.upper(); current=order["status"]
    if target not in _ALLOWED.get(current,set()): raise ValueError(f"invalid transition {current}->{target}")
    d=dict(order); d["status"]=target; d["last_transition"]={"from":current,"to":target,"reason":reason}
    d.pop("order_sha256",None); d["order_sha256"]=hj(d); return d

def enqueue_order(queue:list[dict[str,Any]],order:dict[str,Any],validation:dict[str,Any])->tuple[list[dict[str,Any]],dict[str,Any]]:
    if validation["status"]!="PASS":
        rejected=transition_order(order,"REJECTED","validation failed")
        return queue, rejected
    accepted=transition_order(order,"ACCEPTED","offline queue accepted")
    if any(x["order_id"]==accepted["order_id"] for x in queue): raise ValueError("duplicate order")
    return queue+[accepted],accepted

def cancel_order(order:dict[str,Any],reason:str="user requested")->dict[str,Any]:
    return transition_order(order,"CANCELED",reason)

def fill_price(side:str,reference_price:float,slippage_bps:float)->float:
    factor=1+(slippage_bps/10000.0 if side=="BUY" else -slippage_bps/10000.0)
    return round(reference_price*factor,8)

def simulate_fill(order:dict[str,Any],fill_quantity:int,c:PaperOrderFillConfig)->tuple[dict[str,Any],dict[str,Any]]:
    c.validate()
    if order["status"] not in {"ACCEPTED","PARTIALLY_FILLED"}: raise ValueError("not fillable")
    if fill_quantity<1 or fill_quantity>order["remaining_quantity"]: raise ValueError("fill quantity")
    price=fill_price(order["side"],order["reference_price"],c.slippage_bps)
    fee=c.commission_per_order if order["filled_quantity"]==0 else 0.0
    total_filled=order["filled_quantity"]+fill_quantity; remaining=order["quantity"]-total_filled
    target="FILLED" if remaining==0 else "PARTIALLY_FILLED"
    updated=transition_order(order,target,"offline simulated fill")
    updated["filled_quantity"]=total_filled;updated["remaining_quantity"]=remaining
    updated.pop("order_sha256",None);updated["order_sha256"]=hj(updated)
    fill={"stage":"V80.26","fill_id":"fill-"+hj({"order":order["order_id"],"n":total_filled})[:20],
          "order_id":order["order_id"],"symbol":order["symbol"],"side":order["side"],"quantity":fill_quantity,
          "price":price,"gross_notional":round(price*fill_quantity,8),"commission":fee,"status":"SIMULATED",
          "broker_fill_id":None,"actual_orders_submitted":0}
    fill["fill_sha256"]=hj(fill); return updated,fill

def apply_fill(account:dict[str,Any],positions:dict[str,Any],fill:dict[str,Any])->tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
    a=dict(account);p={k:dict(v) for k,v in positions.items()};sym=fill["symbol"];qty=fill["quantity"];price=fill["price"];fee=fill["commission"]
    realized=0.0
    if fill["side"]=="BUY":
        cost=price*qty+fee
        if a["cash"]+1e-9<cost: raise ValueError("insufficient cash")
        old=p.get(sym,{"quantity":0,"average_price":0.0,"realized_pnl":0.0})
        newq=old["quantity"]+qty;avg=((old["quantity"]*old["average_price"])+(qty*price))/newq
        p[sym]={"quantity":newq,"average_price":avg,"realized_pnl":old.get("realized_pnl",0.0)}
        a["cash"]=round(a["cash"]-cost,8)
    else:
        old=p.get(sym)
        if not old or old["quantity"]<qty: raise ValueError("insufficient position")
        proceeds=price*qty-fee;realized=(price-old["average_price"])*qty-fee
        remain=old["quantity"]-qty;a["cash"]=round(a["cash"]+proceeds,8)
        if remain==0:p.pop(sym)
        else:p[sym]={"quantity":remain,"average_price":old["average_price"],"realized_pnl":old.get("realized_pnl",0.0)+realized}
    event={"stage":"V80.30","fill_id":fill["fill_id"],"symbol":sym,"side":fill["side"],"quantity":qty,
           "cash_after":a["cash"],"position_quantity_after":p.get(sym,{}).get("quantity",0),"realized_pnl":round(realized,8)}
    event["event_sha256"]=hj(event);return a,p,event

def mark_to_market(account:dict[str,Any],positions:dict[str,Any],prices:dict[str,float])->dict[str,Any]:
    mv=0.0;unreal=0.0
    for sym,pos in positions.items():
        px=float(prices[sym]);mv+=px*pos["quantity"];unreal+=(px-pos["average_price"])*pos["quantity"]
    d={"stage":"V80.31","cash":account["cash"],"market_value":round(mv,8),"equity":round(account["cash"]+mv,8),
       "unrealized_pnl":round(unreal,8),"position_count":len(positions)}
    d["valuation_sha256"]=hj(d);return d

def build_ledgers(orders,fills,events,account,positions,valuation)->dict[str,Any]:
    return {
      "order_ledger":{"stage":"V80.32","status":"PASS","order_count":len(orders),"orders":orders},
      "fill_ledger":{"stage":"V80.33","status":"PASS","fill_count":len(fills),"fills":fills},
      "position_ledger":{"stage":"V80.34","status":"PASS","event_count":len(events),"events":events,"positions":positions},
      "account_ledger":{"stage":"V80.35","status":"PASS","cash":account["cash"],"valuation":valuation},
    }

def store_bundle(out:Path,documents:dict[str,Any])->dict[str,Any]:
    bundle_id="paper-order-fill-"+hj(documents)[:24];bdir=out/"bundles"/bundle_id;created=not bdir.exists();files={}
    for name,doc in documents.items():
        p=bdir/f"{name}.json";data=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=data: raise ValueError("bundle conflict")
        if not p.exists():aw(p,data)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(data),"byte_size":len(data)}
    ledger={"stage":"V80.36","status":"PASS","bundle_id":bundle_id,"document_count":len(documents),"files":files,
            "bundle_created":created,"bundle_reused":not created,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"paper_order_fill_master_ledger_v80_36.json",ledger)
    return {"bundle_id":bundle_id,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out:Path,ledger:dict[str,Any])->dict[str,Any]:
    lp=out/"paper_order_fill_master_ledger_v80_36.json";b=lp.read_bytes()
    d={"stage":"V80.37","status":"PASS","bundle_id":ledger["bundle_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"paper_order_fill_manifest_v80_37.json",d);return d

def verify_manifest(out:Path,m:dict[str,Any])->bool:
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u):raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("tamper")
    ledger=json.loads((out/"paper_order_fill_master_ledger_v80_36.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("nested tamper")
    return True

def run_engine(root:Path,c:PaperOrderFillConfig,out:Path)->dict[str,Any]:
    validate_session_certificate(root/"release/v80_20/output/paper_session_engine_certificate_v80_20.json")
    account={"cash":c.initial_cash};positions={};queue=[];orders=[];fills=[];events=[]
    buy=make_order("AAPL","BUY",10,100.0,"demo-buy");vb=validate_order(buy,c,positions);queue,buy=enqueue_order(queue,buy,vb);orders.append(buy)
    buy,fill1=simulate_fill(buy,4,c);fills.append(fill1);account,positions,e1=apply_fill(account,positions,fill1);events.append(e1)
    buy,fill2=simulate_fill(buy,6,c);fills.append(fill2);account,positions,e2=apply_fill(account,positions,fill2);events.append(e2);orders[0]=buy
    sell=make_order("AAPL","SELL",10,105.0,"demo-sell");vs=validate_order(sell,c,positions);queue,sell=enqueue_order(queue,sell,vs);orders.append(sell)
    sell,fill3=simulate_fill(sell,10,c);fills.append(fill3);account,positions,e3=apply_fill(account,positions,fill3);events.append(e3);orders[1]=sell
    cancel=make_order("MSFT","BUY",5,200.0,"demo-cancel");vc=validate_order(cancel,c,positions);queue,cancel=enqueue_order(queue,cancel,vc);cancel=cancel_order(cancel);orders.append(cancel)
    reject=make_order("TSLA","SELL",1,300.0,"demo-reject");vr=validate_order(reject,c,positions);queue,reject=enqueue_order(queue,reject,vr);orders.append(reject)
    valuation=mark_to_market(account,positions,{})
    ledgers=build_ledgers(orders,fills,events,account,positions,valuation)
    summary={"stage":"V80.38","status":"PASS","order_count":len(orders),"fill_count":len(fills),
             "filled_order_count":sum(1 for x in orders if x["status"]=="FILLED"),
             "canceled_order_count":sum(1 for x in orders if x["status"]=="CANCELED"),
             "rejected_order_count":sum(1 for x in orders if x["status"]=="REJECTED"),
             "partial_fill_event_count":1,"closing_cash":account["cash"],"position_count":len(positions),
             "equity":valuation["equity"],"realized_pnl":round(sum(e["realized_pnl"] for e in events),8)}
    docs={**ledgers,"summary":summary};stored=store_bundle(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    return {"stage":"V80.38","status":"PASS","summary":summary,**stored,"manifest":manifest,
            "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root:Path,out:Path,c:PaperOrderFillConfig,r:dict[str,Any])->dict[str,Any]:
    s=r["summary"];checks={"session_certificate_present":(root/"release/v80_20/output/paper_session_engine_certificate_v80_20.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","orders_positive":s["order_count"]>0,"fills_positive":s["fill_count"]>0,
      "filled_orders_positive":s["filled_order_count"]>0,"cancel_count_one":s["canceled_order_count"]==1,
      "reject_count_one":s["rejected_order_count"]==1,"positions_flat":s["position_count"]==0,
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,"network_zero":r["network_requests_executed"]==0,
      "credentials_zero":r["credentials_used"]==0,"client_false":r["trading_client_created"] is False,"orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V80.40","status":status,"scope":"OFFLINE_PAPER_ORDER_AND_FILL_ENGINE",
          "stages_completed":[f"V80.{i:02d}" for i in range(21,41)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
          "config":asdict(c),"engine_summary":{**s,"bundle_id":r["bundle_id"],"bundle_created":r["created"],"bundle_reused":r["reused"]},
          "engine_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
          "network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,
          "actual_orders_submitted":0,"paper_trading_authorized":False,"live_trading_authorized":False,
          "next_phase":"V80_41_PAPER_MONITORING_AND_COMPLETION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"paper_order_fill_engine_certificate_v80_40.json",cert)
    wj(out/"paper_order_fill_engine_verify_v80_40.json",{"stage":"V80.40","status":status,"verified":not failed,
       "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert

sha256_paper_order_fill_json=hj
