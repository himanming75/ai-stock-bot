from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
import hashlib, json

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def safety() -> dict:
    return {
        "environment":"offline",
        "network_allowed":False,
        "broker_connected":False,
        "actual_orders_submitted":0,
        "live_trading_authorized":False,
        "live_deployment_approved":False,
        "real_credentials_allowed":False,
    }

@dataclass(frozen=True)
class Quote:
    symbol: str
    timestamp: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    quote_sha256: str

@dataclass(frozen=True)
class Bar:
    symbol: str
    timestamp: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    bar_sha256: str

def quote_hash_payload(symbol:str,timestamp:str,bid:float,ask:float,bid_size:int,ask_size:int)->dict:
    return {"symbol":symbol,"timestamp":timestamp,"bid":bid,"ask":ask,"bid_size":bid_size,"ask_size":ask_size}

def bar_hash_payload(symbol:str,timestamp:str,timeframe:str,open_:float,high:float,low:float,close:float,volume:int)->dict:
    return {"symbol":symbol,"timestamp":timestamp,"timeframe":timeframe,"open":open_,"high":high,"low":low,"close":close,"volume":volume}

class OfflineMarketDataAdapter:
    def __init__(self, timezone: str = "America/New_York"):
        self.timezone = timezone
        self.quotes: list[Quote] = []
        self.bars: list[Bar] = []
        self._quote_keys:set[tuple[str,str]] = set()
        self._bar_keys:set[tuple[str,str,str]] = set()
        self.network_allowed=False
        self.broker_connected=False
        self.actual_orders_submitted=0

    def make_quote(self,symbol:str,timestamp:datetime,bid:float,ask:float,bid_size:int,ask_size:int)->Quote:
        if timestamp.tzinfo is None:
            raise ValueError("timezone-aware timestamp required")
        symbol=symbol.upper().strip()
        if not symbol: raise ValueError("symbol required")
        if bid<=0 or ask<=0 or ask<bid: raise ValueError("invalid quote prices")
        if bid_size<0 or ask_size<0: raise ValueError("invalid quote sizes")
        ts=timestamp.astimezone(ZoneInfo(self.timezone)).isoformat()
        payload=quote_hash_payload(symbol,ts,float(bid),float(ask),int(bid_size),int(ask_size))
        return Quote(symbol,ts,float(bid),float(ask),int(bid_size),int(ask_size),digest_json(payload))

    def make_bar(self,symbol:str,timestamp:datetime,timeframe:str,open_:float,high:float,low:float,close:float,volume:int)->Bar:
        if timestamp.tzinfo is None:
            raise ValueError("timezone-aware timestamp required")
        symbol=symbol.upper().strip()
        if not symbol: raise ValueError("symbol required")
        if timeframe not in ("1m","5m","1d"): raise ValueError("unsupported timeframe")
        prices=[float(open_),float(high),float(low),float(close)]
        if min(prices)<=0: raise ValueError("prices must be positive")
        if high<max(open_,close) or low>min(open_,close) or high<low:
            raise ValueError("invalid OHLC relationship")
        if volume<0: raise ValueError("volume must be non-negative")
        ts=timestamp.astimezone(ZoneInfo(self.timezone)).isoformat()
        payload=bar_hash_payload(symbol,ts,timeframe,*prices,int(volume))
        return Bar(symbol,ts,timeframe,*prices,int(volume),digest_json(payload))

    def append_quote(self,quote:Quote)->None:
        key=(quote.symbol,quote.timestamp)
        if key in self._quote_keys: raise ValueError("duplicate quote")
        expected=digest_json(quote_hash_payload(quote.symbol,quote.timestamp,quote.bid,quote.ask,quote.bid_size,quote.ask_size))
        if expected!=quote.quote_sha256: raise ValueError("quote hash mismatch")
        if self.quotes and quote.timestamp<=self.quotes[-1].timestamp:
            raise ValueError("quote timestamp not increasing")
        self.quotes.append(quote);self._quote_keys.add(key)

    def append_bar(self,bar:Bar)->None:
        key=(bar.symbol,bar.timeframe,bar.timestamp)
        if key in self._bar_keys: raise ValueError("duplicate bar")
        expected=digest_json(bar_hash_payload(bar.symbol,bar.timestamp,bar.timeframe,bar.open,bar.high,bar.low,bar.close,bar.volume))
        if expected!=bar.bar_sha256: raise ValueError("bar hash mismatch")
        same=[x for x in self.bars if x.symbol==bar.symbol and x.timeframe==bar.timeframe]
        if same and bar.timestamp<=same[-1].timestamp:
            raise ValueError("bar timestamp not increasing")
        self.bars.append(bar);self._bar_keys.add(key)

    def health(self)->dict:
        return {"status":"HEALTHY","mode":"offline_market_data","network_allowed":False,
                "broker_connected":False,"actual_orders_submitted":0,
                "quote_count":len(self.quotes),"bar_count":len(self.bars)}

def validate_market_data(quotes:list[Quote],bars:list[Bar],expected_interval_minutes:int=1)->dict:
    errors=[];gaps=[];duplicate_keys=[]
    qseen=set()
    for q in quotes:
        key=(q.symbol,q.timestamp)
        if key in qseen: duplicate_keys.append(f"quote:{q.symbol}:{q.timestamp}")
        qseen.add(key)
        if q.ask<q.bid: errors.append(f"crossed_quote:{q.timestamp}")
    grouped={}
    for b in bars:
        key=(b.symbol,b.timeframe,b.timestamp)
        if key in qseen: pass
        grouped.setdefault((b.symbol,b.timeframe),[]).append(b)
        if b.high<max(b.open,b.close) or b.low>min(b.open,b.close) or b.high<b.low:
            errors.append(f"ohlc:{b.timestamp}")
    for key,items in grouped.items():
        ordered=sorted(items,key=lambda x:x.timestamp)
        seen=set()
        for i,b in enumerate(ordered):
            k=(b.symbol,b.timeframe,b.timestamp)
            if k in seen: duplicate_keys.append(f"bar:{b.symbol}:{b.timeframe}:{b.timestamp}")
            seen.add(k)
            if i:
                prev=datetime.fromisoformat(ordered[i-1].timestamp)
                cur=datetime.fromisoformat(b.timestamp)
                delta=int((cur-prev).total_seconds()//60)
                if delta>expected_interval_minutes:
                    gaps.append({"symbol":b.symbol,"timeframe":b.timeframe,
                                 "previous_timestamp":ordered[i-1].timestamp,
                                 "current_timestamp":b.timestamp,
                                 "gap_minutes":delta-expected_interval_minutes})
    return {"verified":not errors and not duplicate_keys,
            "error_count":len(errors),"errors":errors,
            "duplicate_count":len(duplicate_keys),"duplicates":duplicate_keys,
            "gap_count":len(gaps),"gaps":gaps}

def build_market_data_foundation(certificate_path:Path,config_path:Path,output_dir:Path)->dict:
    cert,config=map(load_json,(certificate_path,config_path));errors=[]
    if cert.get("stage")!="V78.30" or cert.get("status")!="PASS":errors.append("market_clock_certificate")
    if cert.get("certification_scope")!="OFFLINE_MARKET_DATA_ADAPTER_DEVELOPMENT_ONLY":errors.append("certificate_scope")
    md=config.get("market_data",{})
    for key in ("timezone","symbols","timeframes","expected_interval_minutes"):
        if key not in md:errors.append(f"config_{key}")
    status="PASS" if not errors else "FAIL"
    doc={"schema_version":"v78.31.market_data_foundation.1","stage":"V78.31","status":status,
         "scope":"OFFLINE_MARKET_DATA_ONLY","champion_candidate":cert.get("champion_candidate"),
         "market_data":md,"error_count":len(errors),"errors":errors,**safety(),
         "next_phase":"V78_32_OFFLINE_QUOTE_BAR_FEED"}
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"market_data_adapter_foundation_v78_31.json",doc)
    ver={"stage":"V78.31","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"market_data_adapter_foundation_verification_v78_31.json",ver);return doc

def run_offline_quote_bar_feed(foundation_path:Path,output_dir:Path)->dict:
    foundation=load_json(foundation_path);errors=[]
    if foundation.get("stage")!="V78.31" or foundation.get("status")!="PASS":errors.append("foundation_input")
    cfg=foundation.get("market_data",{});tz=ZoneInfo(cfg.get("timezone","America/New_York"))
    adapter=OfflineMarketDataAdapter(cfg.get("timezone","America/New_York"))
    base=datetime(2026,7,6,9,30,tzinfo=tz)
    try:
        for i in range(3):
            adapter.append_quote(adapter.make_quote("AAPL",base+timedelta(minutes=i),100+i*.1,100.05+i*.1,100,120))
            adapter.append_bar(adapter.make_bar("AAPL",base+timedelta(minutes=i),"1m",
                100+i*.1,100.2+i*.1,99.9+i*.1,100.1+i*.1,1000+i*10))
    except Exception as exc:errors.append(f"feed_exception:{type(exc).__name__}")
    checks={"quote_count":len(adapter.quotes)==3,"bar_count":len(adapter.bars)==3,
            "quotes_monotonic":[x.timestamp for x in adapter.quotes]==sorted(x.timestamp for x in adapter.quotes),
            "bars_monotonic":[x.timestamp for x in adapter.bars]==sorted(x.timestamp for x in adapter.bars),
            "network_disabled":adapter.health()["network_allowed"] is False,
            "actual_orders_zero":adapter.health()["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("offline_feed_checks")
    status="PASS" if not errors else "FAIL"
    doc={"schema_version":"v78.32.offline_quote_bar_feed.1","stage":"V78.32","status":status,
         "quotes":[asdict(x) for x in adapter.quotes],"bars":[asdict(x) for x in adapter.bars],
         "checks":checks,"failed_checks":failed,"error_count":len(errors),"errors":errors,**safety(),
         "next_phase":"V78_33_MARKET_DATA_VALIDATION_GAP_DETECTION"}
    doc["feed_sha256"]=digest_json({k:v for k,v in doc.items() if k!="feed_sha256"})
    write_json(output_dir/"offline_quote_bar_feed_v78_32.json",doc)
    ver={"stage":"V78.32","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"feed_sha256":doc["feed_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"offline_quote_bar_feed_verification_v78_32.json",ver);return doc

def run_market_data_validation(foundation_path:Path,feed_path:Path,output_dir:Path)->dict:
    foundation,feed=map(load_json,(foundation_path,feed_path));errors=[]
    if foundation.get("stage")!="V78.31" or foundation.get("status")!="PASS":errors.append("foundation_input")
    if feed.get("stage")!="V78.32" or feed.get("status")!="PASS":errors.append("feed_input")
    quotes=[Quote(**x) for x in feed.get("quotes",[])]
    bars=[Bar(**x) for x in feed.get("bars",[])]
    validation=validate_market_data(quotes,bars,int(foundation.get("market_data",{}).get("expected_interval_minutes",1)))
    gap_bars=list(bars)
    if len(gap_bars)>=3:
        b=gap_bars[2]
        shifted=datetime.fromisoformat(b.timestamp)+timedelta(minutes=2)
        gap_bars[2]=Bar(b.symbol,shifted.isoformat(),b.timeframe,b.open,b.high,b.low,b.close,b.volume,
                        digest_json(bar_hash_payload(b.symbol,shifted.isoformat(),b.timeframe,b.open,b.high,b.low,b.close,b.volume)))
    gap_validation=validate_market_data(quotes,gap_bars,1)
    checks={"clean_feed_verified":validation["verified"] is True,
            "clean_feed_no_duplicates":validation["duplicate_count"]==0,
            "clean_feed_no_gaps":validation["gap_count"]==0,
            "synthetic_gap_detected":gap_validation["gap_count"]==1,
            "gap_minutes_expected":gap_validation["gaps"][0]["gap_minutes"]==2}
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("market_data_validation_checks")
    status="PASS" if not errors else "FAIL"
    doc={"schema_version":"v78.33.market_data_validation.1","stage":"V78.33","status":status,
         "validation":validation,"synthetic_gap_validation":gap_validation,
         "checks":checks,"failed_checks":failed,"error_count":len(errors),"errors":errors,**safety(),
         "next_phase":"V78_34_MARKET_DATA_SAFETY_GATE"}
    doc["validation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="validation_sha256"})
    write_json(output_dir/"market_data_validation_gap_detection_v78_33.json",doc)
    ver={"stage":"V78.33","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"validation_sha256":doc["validation_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"market_data_validation_gap_detection_verification_v78_33.json",ver);return doc

def run_market_data_safety_gate(foundation_path:Path,feed_path:Path,validation_path:Path,output_dir:Path)->dict:
    foundation,feed,validation=map(load_json,(foundation_path,feed_path,validation_path));errors=[]
    for expected,doc in (("V78.31",foundation),("V78.32",feed),("V78.33",validation)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":errors.append(expected)
    quotes=feed.get("quotes",[]);bars=feed.get("bars",[])
    checks={"offline_scope":foundation.get("scope")=="OFFLINE_MARKET_DATA_ONLY",
            "quote_hashes_unique":len({x["quote_sha256"] for x in quotes})==len(quotes),
            "bar_hashes_unique":len({x["bar_sha256"] for x in bars})==len(bars),
            "feed_checks_passed":feed.get("failed_checks")==[],
            "validation_checks_passed":validation.get("failed_checks")==[],
            "clean_validation_verified":validation.get("validation",{}).get("verified") is True,
            "network_disabled":all(x.get("network_allowed") is False for x in (foundation,feed,validation)),
            "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,feed,validation)),
            "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,feed,validation))}
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("market_data_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={"schema_version":"v78.34.market_data_safety_gate.1","stage":"V78.34","status":status,
         "gate_scope":"OFFLINE_STRATEGY_RUNTIME_ELIGIBILITY_ONLY",
         "decision":"ALLOW_OFFLINE_STRATEGY_RUNTIME" if not errors else "BLOCK_STRATEGY_RUNTIME",
         "real_broker_connection_approved":False,"actual_order_submission_approved":False,
         "checks":checks,"failed_checks":failed,"error_count":len(errors),"errors":errors,**safety(),
         "next_phase":"V78_35_MARKET_DATA_ADAPTER_CERTIFICATE"}
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"market_data_safety_gate_v78_34.json",doc)
    ver={"stage":"V78.34","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"safety_gate_sha256":doc["safety_gate_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"market_data_safety_gate_verification_v78_34.json",ver);return doc

def issue_market_data_certificate(v31:Path,v32:Path,v33:Path,v34:Path,foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v31,v32,v33,v34)));foundation=load_json(foundation_path)
    expected=["V78.31","V78.32","V78.33","V78.34"];errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={"schema_version":"v78.35.market_data_certificate.1","stage":"V78.35",
          "certificate_id":"MARKET-DATA-ADAPTER-V78.35","status":status,
          "decision":"certified_for_offline_strategy_runtime" if not errors else "market_data_rejected",
          "certification_scope":"OFFLINE_STRATEGY_RUNTIME_DEVELOPMENT_ONLY",
          "real_broker_connection_approved":False,"real_credentials_approved":False,
          "network_transport_approved":False,"actual_order_submission_approved":False,
          "live_trading_approved":False,"certified_stages":expected,
          "champion_candidate":foundation.get("champion_candidate"),
          "error_count":len(errors),"errors":errors,**safety(),
          "next_phase":"V78_36_STRATEGY_RUNTIME_FOUNDATION" if not errors else "REPAIR_V78_35"}
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"market_data_adapter_certificate_v78_35.json",cert)
    ver={"stage":"V78.35","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],"next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"market_data_adapter_certificate_verification_v78_35.json",ver);return cert
