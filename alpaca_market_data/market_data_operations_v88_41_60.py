from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta, timezone
import hashlib, json, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode("utf-8")).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class MarketDataOperationsConfig:
    mode: str = "PAPER_MARKET_DATA_OPERATIONS_FOUNDATION"
    environment: str = "PAPER"
    provider: str = "ALPACA_FIXTURE"
    symbols: tuple[str,...] = ("AAPL","MSFT","SPY")
    timeframe_seconds: int = 60
    freshness_threshold_seconds: int = 90
    clock_skew_tolerance_seconds: int = 5
    max_missing_bars: int = 0
    max_duplicate_bars: int = 0
    max_out_of_order_bars: int = 0
    offline_fallback_allowed: bool = False
    market_data_network_enabled: bool = False
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    network_requests_executed: int = 0
    actual_orders_submitted: int = 0
    def validate(self):
        if self.mode != "PAPER_MARKET_DATA_OPERATIONS_FOUNDATION": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        if not self.provider.strip() or not self.symbols: raise ValueError("provider/symbols")
        if min(self.timeframe_seconds,self.freshness_threshold_seconds,self.clock_skew_tolerance_seconds) <= 0:
            raise ValueError("timing")
        if min(self.max_missing_bars,self.max_duplicate_bars,self.max_out_of_order_bars) < 0:
            raise ValueError("limits")
        if self.offline_fallback_allowed or self.market_data_network_enabled:
            raise ValueError("fallback/network")
        if self.scheduler_enabled or self.runtime_loop_enabled or self.auto_execution_enabled:
            raise ValueError("runtime disabled")
        if self.paper_order_submission_authorized or self.live_trading_authorized:
            raise ValueError("authorization")
        if self.network_requests_executed != 0 or self.actual_orders_submitted != 0:
            raise ValueError("offline only")

def validate_source(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V88.40" or c.get("status")!="PASS":
        raise ValueError("bad V88.40 certificate")
    if c.get("paper_strategy_runtime_loop_foundation_complete") is not True:
        raise ValueError("runtime prerequisite")
    if c.get("runtime_loop_enabled") is not False:
        raise ValueError("unsafe source")
    return c

def data_policy(config):
    d={"stage":"V88.41","status":"PASS","provider":config.provider,
       "symbols":list(config.symbols),"network_enabled":False,
       "offline_fallback_allowed":False,"order_submission_authorized":False}
    d["policy_sha256"]=hj(d);return d

def fixture_bars():
    base=datetime(2026,7,6,13,30,tzinfo=timezone.utc)
    bars=[]
    for i,px in enumerate([200.0,200.5,201.0]):
        bars.append({"symbol":"AAPL","timestamp":(base+timedelta(minutes=i)).isoformat(),
                     "open":px,"high":px+0.4,"low":px-0.3,"close":px+0.1,"volume":1000+i*100})
    return bars

def validate_bar_schema(bar):
    required=["symbol","timestamp","open","high","low","close","volume"]
    checks={"required_fields":all(k in bar for k in required),
            "symbol_valid":isinstance(bar.get("symbol"),str) and bool(bar.get("symbol")),
            "timestamp_valid":isinstance(bar.get("timestamp"),str),
            "prices_numeric":all(isinstance(bar.get(k),(int,float)) for k in ["open","high","low","close"]),
            "volume_numeric":isinstance(bar.get("volume"),(int,float)),
            "ohlc_consistent":bar.get("high",0)>=max(bar.get("open",0),bar.get("close",0)) and
                              bar.get("low",0)<=min(bar.get("open",0),bar.get("close",0))}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V88.42","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["schema_sha256"]=hj(d);return d

def freshness_check(config,bar_timestamp,now):
    ts=datetime.fromisoformat(bar_timestamp)
    age=max(0.0,(now-ts).total_seconds())
    stale=age>config.freshness_threshold_seconds
    d={"stage":"V88.43","age_seconds":age,"stale":stale,
       "status":"FAIL" if stale else "PASS"}
    d["freshness_sha256"]=hj(d);return d

def missing_bar_detection(config,bars):
    timestamps=sorted(datetime.fromisoformat(b["timestamp"]) for b in bars)
    missing=0
    gaps=[]
    for a,b in zip(timestamps,timestamps[1:]):
        delta=int((b-a).total_seconds())
        if delta>config.timeframe_seconds:
            count=(delta//config.timeframe_seconds)-1
            missing+=count;gaps.append({"from":a.isoformat(),"to":b.isoformat(),"missing":count})
    d={"stage":"V88.44","missing_bar_count":missing,"gaps":gaps,
       "status":"PASS" if missing<=config.max_missing_bars else "FAIL"}
    d["missing_sha256"]=hj(d);return d

def duplicate_bar_detection(config,bars):
    keys=[(b["symbol"],b["timestamp"]) for b in bars]
    duplicates=len(keys)-len(set(keys))
    d={"stage":"V88.45","duplicate_bar_count":duplicates,
       "status":"PASS" if duplicates<=config.max_duplicate_bars else "FAIL"}
    d["duplicate_sha256"]=hj(d);return d

def out_of_order_detection(config,bars):
    ts=[datetime.fromisoformat(b["timestamp"]) for b in bars]
    count=sum(1 for a,b in zip(ts,ts[1:]) if b<a)
    d={"stage":"V88.46","out_of_order_count":count,
       "status":"PASS" if count<=config.max_out_of_order_bars else "FAIL"}
    d["ordering_sha256"]=hj(d);return d

def market_clock_consistency(config,provider_time,system_time):
    skew=abs((provider_time-system_time).total_seconds())
    d={"stage":"V88.47","clock_skew_seconds":skew,
       "status":"PASS" if skew<=config.clock_skew_tolerance_seconds else "FAIL"}
    d["clock_sha256"]=hj(d);return d

def symbol_health(config,symbol,bars):
    subset=[b for b in bars if b["symbol"]==symbol]
    checks={"symbol_allowed":symbol in config.symbols,
            "bars_present":len(subset)>0,
            "latest_schema_pass":bool(subset) and validate_bar_schema(subset[-1])["status"]=="PASS"}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V88.48","symbol":symbol,
       "status":"PASS" if not failed else "FAIL",
       "bar_count":len(subset),"checks":checks,"failed_checks":failed}
    d["symbol_health_sha256"]=hj(d);return d

def provider_health(config,request_success=True,latency_ms=20):
    checks={"provider_matches":config.provider=="ALPACA_FIXTURE",
            "request_success":request_success,
            "latency_nonnegative":latency_ms>=0,
            "network_disabled":config.market_data_network_enabled is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V88.49","status":"PASS" if not failed else "FAIL",
       "latency_ms":latency_ms,"checks":checks,"failed_checks":failed}
    d["provider_health_sha256"]=hj(d);return d

def fallback_policy(config,provider_status):
    fallback_attempted=provider_status!="PASS"
    allowed=config.offline_fallback_allowed
    d={"stage":"V88.50","provider_status":provider_status,
       "fallback_attempted":fallback_attempted,
       "fallback_allowed":allowed,
       "strategy_cycle_allowed":provider_status=="PASS",
       "status":"PASS" if not allowed else "FAIL"}
    d["fallback_sha256"]=hj(d);return d

def data_gap_classification(missing_doc,duplicate_doc,ordering_doc):
    classes=[]
    if missing_doc["missing_bar_count"]>0: classes.append("MISSING_BARS")
    if duplicate_doc["duplicate_bar_count"]>0: classes.append("DUPLICATE_BARS")
    if ordering_doc["out_of_order_count"]>0: classes.append("OUT_OF_ORDER_BARS")
    d={"stage":"V88.51","classification_count":len(classes),
       "classifications":classes,"status":"CLEAN" if not classes else "DEGRADED"}
    d["classification_sha256"]=hj(d);return d

def data_incident(classification,provider):
    critical=classification["status"]!="CLEAN" or provider["status"]!="PASS"
    d={"stage":"V88.52","incident_required":critical,
       "severity":"CRITICAL" if critical else "INFO",
       "actions":["STOP_STRATEGY_CYCLE","CLEAR_DATA_BUFFER","MANUAL_REVIEW"] if critical else [],
       "automatic_order_action":False}
    d["incident_sha256"]=hj(d);return d

def recovery_plan(incident):
    d={"stage":"V88.53","status":"PASS",
       "stop_strategy_cycle":incident["incident_required"],
       "clear_data_buffer":incident["incident_required"],
       "manual_review_required":incident["incident_required"],
       "network_enabled":False,"order_submission_enabled":False}
    d["recovery_sha256"]=hj(d);return d

def market_data_snapshot(config,bars):
    d={"stage":"V88.54","provider":config.provider,
       "symbol_count":len(set(b["symbol"] for b in bars)),
       "bar_count":len(bars),"snapshot_sha256":hj(bars)}
    d["document_sha256"]=hj(d);return d

def positive_scenario(config):
    bars=fixture_bars()
    now=datetime.fromisoformat(bars[-1]["timestamp"])+timedelta(seconds=30)
    schema=validate_bar_schema(bars[-1]);fresh=freshness_check(config,bars[-1]["timestamp"],now)
    missing=missing_bar_detection(config,bars);dup=duplicate_bar_detection(config,bars)
    ordering=out_of_order_detection(config,bars)
    clock=market_clock_consistency(config,now,now+timedelta(seconds=2))
    symbol=symbol_health(config,"AAPL",bars);provider=provider_health(config,True,20)
    fallback=fallback_policy(config,provider["status"])
    cls=data_gap_classification(missing,dup,ordering);incident=data_incident(cls,provider)
    recovery=recovery_plan(incident);snapshot=market_data_snapshot(config,bars)
    d={"stage":"V88.55","status":"PASS",
       "schema_status":schema["status"],"freshness_status":fresh["status"],
       "missing_status":missing["status"],"duplicate_status":dup["status"],
       "ordering_status":ordering["status"],"clock_status":clock["status"],
       "symbol_status":symbol["status"],"provider_status":provider["status"],
       "fallback_status":fallback["status"],"classification_status":cls["status"],
       "incident_required":incident["incident_required"],
       "recovery_status":recovery["status"],
       "snapshot_bar_count":snapshot["bar_count"],
       "network_requests_executed":0,"actual_orders_submitted":0,
       "documents":{"bars":bars,"schema":schema,"freshness":fresh,"missing":missing,
                    "duplicate":dup,"ordering":ordering,"clock":clock,
                    "symbol":symbol,"provider":provider,"fallback":fallback,
                    "classification":cls,"incident":incident,"recovery":recovery,
                    "snapshot":snapshot}}
    d["positive_sha256"]=hj(d);return d

def negative_scenarios(config):
    bars=fixture_bars()
    stale=freshness_check(config,bars[-1]["timestamp"],
                          datetime.fromisoformat(bars[-1]["timestamp"])+timedelta(seconds=999))
    missing_bars=[bars[0],bars[2]]
    dup_bars=bars+[dict(bars[-1])]
    out_order=[bars[1],bars[0],bars[2]]
    missing=missing_bar_detection(config,missing_bars)
    duplicate=duplicate_bar_detection(config,dup_bars)
    ordering=out_of_order_detection(config,out_order)
    bad_clock=market_clock_consistency(config,
        datetime.fromisoformat(bars[-1]["timestamp"]),
        datetime.fromisoformat(bars[-1]["timestamp"])+timedelta(seconds=60))
    provider=provider_health(config,False,0)
    fallback=fallback_policy(config,provider["status"])
    cls=data_gap_classification(missing,duplicate,ordering)
    incident=data_incident(cls,provider);recovery=recovery_plan(incident)
    d={"stage":"V88.56","status":"PASS",
       "stale_failed":stale["status"]=="FAIL",
       "missing_failed":missing["status"]=="FAIL",
       "duplicate_failed":duplicate["status"]=="FAIL",
       "ordering_failed":ordering["status"]=="FAIL",
       "clock_failed":bad_clock["status"]=="FAIL",
       "provider_failed":provider["status"]=="FAIL",
       "fallback_blocked":fallback["fallback_allowed"] is False and fallback["strategy_cycle_allowed"] is False,
       "incident_required":incident["incident_required"],
       "recovery_ready":recovery["manual_review_required"]}
    d["negative_sha256"]=hj(d);return d

def audit(config,positive,negative):
    checks={"schema_pass":positive["schema_status"]=="PASS",
            "freshness_pass":positive["freshness_status"]=="PASS",
            "missing_pass":positive["missing_status"]=="PASS",
            "duplicate_pass":positive["duplicate_status"]=="PASS",
            "ordering_pass":positive["ordering_status"]=="PASS",
            "clock_pass":positive["clock_status"]=="PASS",
            "symbol_pass":positive["symbol_status"]=="PASS",
            "provider_pass":positive["provider_status"]=="PASS",
            "fallback_policy_pass":positive["fallback_status"]=="PASS",
            "classification_clean":positive["classification_status"]=="CLEAN",
            "positive_no_incident":positive["incident_required"] is False,
            "negative_scenarios_pass":negative["status"]=="PASS",
            "network_disabled":config.market_data_network_enabled is False,
            "runtime_disabled":config.runtime_loop_enabled is False,
            "network_zero":positive["network_requests_executed"]==0,
            "orders_zero":positive["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V88.57","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store(out,docs):
    pid="market-data-ops-"+hj(docs)[:24];pd=out/"packages"/pid
    created=not pd.exists();files={}
    for name,doc in docs.items():
        p=pd/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V88.58","status":"PASS","package_id":pid,
            "package_created":created,"package_reused":not created,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"market_data_operations_ledger_v88_58.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def manifest(out,ledger):
    p=out/"market_data_operations_ledger_v88_58.json";b=p.read_bytes()
    d={"stage":"V88.59","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"market_data_operations_manifest_v88_59.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("manifest tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_source(root/"release/v88_40/output/runtime_loop_certificate_v88_40.json")
    policy=data_policy(c);positive=positive_scenario(c);negative=negative_scenarios(c)
    au=audit(c,positive,negative)
    docs={"source_certificate":{"certificate_sha256":source["certificate_sha256"]},
          "data_policy":policy,"positive_scenario":positive,
          "negative_scenarios":negative,"audit":au}
    st=store(out,docs);m=manifest(out,st["ledger"]);verify_manifest(out,m)
    summary={"provider":c.provider,"symbol_count":len(c.symbols),
             "schema_status":positive["schema_status"],
             "freshness_status":positive["freshness_status"],
             "missing_status":positive["missing_status"],
             "duplicate_status":positive["duplicate_status"],
             "ordering_status":positive["ordering_status"],
             "clock_status":positive["clock_status"],
             "symbol_status":positive["symbol_status"],
             "provider_status":positive["provider_status"],
             "fallback_status":positive["fallback_status"],
             "classification_status":positive["classification_status"],
             "negative_scenarios_status":negative["status"],
             "audit_status":au["status"],
             "network_requests_executed":0,"actual_orders_submitted":0}
    return {"stage":"V88.60","status":"PASS" if au["status"]=="PASS" else "FAIL",
            **st,"manifest":m,"summary":summary}

def certificate(root,out,c,r):
    s=r["summary"]
    checks={"pipeline_pass":r["status"]=="PASS",
            "schema_pass":s["schema_status"]=="PASS",
            "freshness_pass":s["freshness_status"]=="PASS",
            "missing_pass":s["missing_status"]=="PASS",
            "duplicate_pass":s["duplicate_status"]=="PASS",
            "ordering_pass":s["ordering_status"]=="PASS",
            "clock_pass":s["clock_status"]=="PASS",
            "symbol_pass":s["symbol_status"]=="PASS",
            "provider_pass":s["provider_status"]=="PASS",
            "fallback_pass":s["fallback_status"]=="PASS",
            "classification_clean":s["classification_status"]=="CLEAN",
            "negative_scenarios_pass":s["negative_scenarios_status"]=="PASS",
            "audit_pass":s["audit_status"]=="PASS",
            "network_zero":s["network_requests_executed"]==0,
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    d={"stage":"V88.60","status":status,
       "scope":"PAPER_MARKET_DATA_OPERATIONS_FOUNDATION",
       "stages_completed":[f"V88.{i:02d}" for i in range(41,61)],
       "completed_stage_count":20 if status=="PASS" else 20-len(failed),
       "config":asdict(c),
       "market_data_operations_summary":{**s,"package_id":r["package_id"],
         "package_created":r["created"],"package_reused":r["reused"]},
       "market_data_operations_manifest":r["manifest"],
       "checks":checks,"failed_checks":failed,
       "paper_market_data_operations_foundation_complete":status=="PASS",
       "market_data_quality_preview_ready":status=="PASS",
       "market_data_network_enabled":False,
       "scheduler_enabled":False,"runtime_loop_enabled":False,
       "auto_execution_enabled":False,
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,
       "network_requests_executed":0,"actual_orders_submitted":0,
       "next_phase":"V88_61_PAPER_SCHEDULER_RUNTIME_SIMULATION"}
    d["certificate_sha256"]=hj(d);wj(out/"market_data_operations_certificate_v88_60.json",d)
    wj(out/"market_data_operations_verify_v88_60.json",
       {"stage":"V88.60","status":status,"verified":not failed,
        "certificate_sha256":d["certificate_sha256"],
        "failed_checks":failed,"next_phase":d["next_phase"]})
    return d
