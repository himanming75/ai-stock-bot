from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import json, math

ID_KEYS={"order_id","client_order_id","trade_id","position_id","parent_order_id","execution_id","fill_id"}
EVENT_KEYS={"event_type","event","stage","status","state","type"}
SIDE_KEYS={"side","action","order_side","position_side"}
SYMBOL_KEYS={"symbol","ticker"}
PRICE_STRONG={"filled_avg_price","fill_price","filled_price","avg_fill_price","average_fill_price","execution_price"}
QTY_STRONG={"filled_qty","filled_quantity","executed_qty","executed_quantity"}
TIME_KEYS={"filled_at","fill_time","executed_at","execution_time","timestamp_utc","timestamp","time","updated_at","created_at"}
FEE_KEYS={"commission","fee","fees","transaction_fee"}
MAX_DEPTH=8; EXIT_WINDOW=600; STRONG_EXIT_WINDOW=120; ENTRY_LOOKBACK=30*24*60*60

def num(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except Exception: return None

def parse_time(v):
    if v in (None,""): return None
    s=str(v).strip()
    try:
        if s.endswith("Z"): s=s[:-1]+"+00:00"
        d=datetime.fromisoformat(s)
        if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception: return None

def walk(obj,path="",depth=0):
    if depth>MAX_DEPTH: return
    if isinstance(obj,dict):
        for k,v in obj.items():
            p=f"{path}.{k}" if path else str(k); yield p,str(k),v
            if isinstance(v,(dict,list)): yield from walk(v,p,depth+1)
    elif isinstance(obj,list):
        for i,v in enumerate(obj[:250]):
            p=f"{path}[{i}]"
            if isinstance(v,(dict,list)): yield from walk(v,p,depth+1)

def vals(rec,keys):
    w={x.lower() for x in keys}; return [(p,k.lower(),v) for p,k,v in walk(rec) if k.lower() in w and v is not None]

def first(rec,strong,weak=()):
    a=vals(rec,strong)
    if a: return a[0][2],a[0][0]
    a=vals(rec,weak)
    return (a[0][2],a[0][0]) if a else (None,None)

def ids(rec):
    out={}
    for _,k,v in vals(rec,ID_KEYS):
        s=str(v).strip()
        if s: out.setdefault(k,set()).add(s)
    return {k:sorted(v) for k,v in out.items()}

def flat_ids(m):
    out=set()
    for k,items in (m or {}).items():
        if k in ID_KEYS: out.update(str(x).strip() for x in items if str(x).strip())
    return out

def fill_evidence(rec):
    text=" ".join(str(v).upper() for _,_,v in vals(rec,EVENT_KEYS))
    return any(t in text for t in ("FILL","FILLED","EXECUTION")) or bool(vals(rec,PRICE_STRONG) and vals(rec,QTY_STRONG))

def normalize_fill(rec,source):
    if not fill_evidence(rec): return None
    side,_=first(rec,SIDE_KEYS); side=str(side or "").upper()
    if side not in {"BUY","SELL"}: return None
    pr,pp=first(rec,PRICE_STRONG,{"price"}); qr,qp=first(rec,QTY_STRONG,{"qty","quantity"}); tr,tp=first(rec,TIME_KEYS); sr,sp=first(rec,SYMBOL_KEYS)
    price,qty,t=num(pr),num(qr),parse_time(tr)
    if price is None or qty is None or t is None or price<=0 or qty<=0: return None
    fees=0.0
    for _,_,v in vals(rec,FEE_KEYS):
        x=num(v)
        if x is not None: fees+=abs(x)
    return {"time":t.isoformat(),"_time":t,"symbol":str(sr or "UNKNOWN").upper(),"side":side,"price":price,"qty":qty,"identifiers":ids(rec),"source":source,"fees_observed":fees,"provenance":{"price_path":pp,"qty_path":qp,"time_path":tp,"symbol_path":sp}}

def read_records(p):
    try:
        if p.suffix.lower()==".jsonl":
            out=[]
            for line in p.read_text(encoding="utf-8",errors="replace").splitlines()[-12000:]:
                try:
                    x=json.loads(line)
                    if isinstance(x,dict): out.append(x)
                except Exception: pass
            return out
        x=json.loads(p.read_text(encoding="utf-8-sig",errors="replace"))
        if isinstance(x,dict): return [x]
        if isinstance(x,list): return [i for i in x if isinstance(i,dict)]
    except Exception: pass
    return []

def collect_fills(root:Path):
    runtime=root/"runtime"; items=[]
    if not runtime.exists(): return [],[]
    tokens=("order","fill","trade","position","broker","paper","execution","ledger","snapshot")
    for p in runtime.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".json",".jsonl"} and any(t in p.name.lower() for t in tokens):
            try: items.append((p.stat().st_mtime,p))
            except Exception: pass
    fills=[]; sources=set(); seen=set()
    for _,p in sorted(items,reverse=True)[:260]:
        rel=str(p.relative_to(root)).replace("\\","/")
        for rec in read_records(p):
            f=normalize_fill(rec,rel)
            if not f: continue
            key=(f["time"],f["symbol"],f["side"],round(f["price"],8),round(f["qty"],8),tuple(sorted(flat_ids(f["identifiers"]))))
            if key in seen: continue
            seen.add(key); fills.append(f); sources.add(rel)
    fills.sort(key=lambda x:x["_time"]); return fills,sorted(sources)

def trade_ids(t):
    out=set(); rid=str(t.get("record_id") or "").strip()
    if rid: out.add(rid)
    out.update(flat_ids((t.get("normalization") or {}).get("identifiers") or {})); return out

def qmatch(a,b):
    return a is not None and b is not None and abs(a-b)<=max(1e-6,1e-6*max(abs(a),abs(b),1.0))

def reconstruct_trade(trade,fills):
    if trade.get("pnl") is not None: return {"status":"NOT_NEEDED","confidence":"ORIGINAL_PNL"}
    ct=parse_time(trade.get("time"))
    if ct is None: return {"status":"UNRESOLVED","reason":"NO_CLOSE_TIME"}
    symbol=str(trade.get("symbol") or "UNKNOWN").upper(); qty=num(trade.get("qty")); tids=trade_ids(trade); exits=[]
    for f in fills:
        delta=abs((f["_time"]-ct).total_seconds())
        if delta>EXIT_WINDOW: continue
        overlap=flat_ids(f["identifiers"]).intersection(tids)
        if overlap: exits.append((100,delta,"IDENTIFIER_OVERLAP",sorted(overlap),f))
        elif symbol!="UNKNOWN" and f["symbol"]==symbol and qty is not None and qmatch(f["qty"],qty) and delta<=STRONG_EXIT_WINDOW:
            exits.append((70,delta,"SYMBOL_QTY_CLOSE_TIME",[],f))
    exits.sort(key=lambda x:(-x[0],x[1]))
    if not exits: return {"status":"UNRESOLVED","reason":"NO_STRONG_EXIT_FILL_MATCH"}
    score,delta,reason,overlap,exitf=exits[0]
    entries=[]
    for f in fills:
        sec=(exitf["_time"]-f["_time"]).total_seconds()
        if f is not exitf and f["symbol"]==exitf["symbol"] and f["side"]!=exitf["side"] and qmatch(f["qty"],exitf["qty"]) and 0<sec<=ENTRY_LOOKBACK:
            entries.append((sec,f))
    entries.sort(key=lambda x:x[0])
    if not entries: return {"status":"UNRESOLVED","reason":"NO_OPPOSITE_ENTRY_FILL"}
    entry=entries[0][1]; q=min(entry["qty"],exitf["qty"])
    gross=(exitf["price"]-entry["price"])*q if entry["side"]=="BUY" else (entry["price"]-exitf["price"])*q
    fees=entry.get("fees_observed",0)+exitf.get("fees_observed",0)
    return {"status":"RECONSTRUCTED","confidence":"HIGH" if reason=="IDENTIFIER_OVERLAP" else "MEDIUM","method":"ACTUAL_FILL_PRICE_DIFFERENCE","pnl":gross-fees,"gross_pnl":gross,"observed_fees":fees,"fee_policy":"ONLY_EXPLICIT_STORED_FEES_SUBTRACTED","entry":{"time":entry["time"],"symbol":entry["symbol"],"side":entry["side"],"price":entry["price"],"qty":entry["qty"],"source":entry["source"]},"exit":{"time":exitf["time"],"symbol":exitf["symbol"],"side":exitf["side"],"price":exitf["price"],"qty":exitf["qty"],"source":exitf["source"]},"exit_match":{"reason":reason,"delta_seconds":delta,"id_overlap":overlap}}

def reconstruct_missing_pnl(root:Path,trades):
    fills,sources=collect_fills(root); counts=Counter(); conf=Counter(); reasons=Counter(); samples=[]
    for trade in trades:
        r=reconstruct_trade(trade,fills); trade["reconstruction"]=r
        if trade.get("pnl") is None and r.get("status")=="RECONSTRUCTED":
            trade["pnl"]=r["pnl"]; n=trade.setdefault("normalization",{}); n["pnl_recovered"]=True; n["pnl_path"]="V3.7_CROSS_LEDGER_ACTUAL_FILL_RECONSTRUCTION"; n["pnl_key"]="reconstructed_from_actual_fills"
        counts[r.get("status","UNKNOWN")]+=1
        if r.get("confidence"): conf[r["confidence"]]+=1
        if r.get("status")=="UNRESOLVED": reasons[r.get("reason","UNKNOWN")]+=1
        if len(samples)<20: samples.append({"closed_trade_time":trade.get("time"),"symbol":trade.get("symbol"),"pnl":trade.get("pnl"),"source":trade.get("source"),"reconstruction":r})
    rc=counts["RECONSTRUCTED"]
    audit={"fill_record_count":len(fills),"fill_source_count":len(sources),"fill_sources":sources,"closed_trade_count":len(trades),"reconstructed_trade_count":rc,"unresolved_trade_count":counts["UNRESOLVED"],"original_pnl_trade_count":counts["NOT_NEEDED"],"confidence_counts":dict(conf),"unresolved_reason_counts":dict(reasons),"samples":samples,"status":"PASS_RECONSTRUCTED" if rc else "PASS_DIAGNOSTIC_NO_SAFE_MATCH","contracts":{"actual_fill_records_only":True,"price_guessing_used":False,"market_price_estimation_used":False,"unobserved_fee_estimation_used":False,"runtime_source_files_modified":False,"broker_network_used":False,"broker_write_performed":False,"order_submission_performed":False}}
    return trades,audit
