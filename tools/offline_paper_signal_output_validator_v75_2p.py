from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2P"
SCHEMA="v75.2p.offline_paper_signal_output_validation.1"
SOURCE_SCHEMA="v75.2o.offline_paper_signal_generation_execution.1"

class SignalOutputValidationError(ValueError): pass

def canonical_json(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(x:Any)->str:
    return hashlib.sha256(canonical_json(x).encode()).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: x=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise SignalOutputValidationError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise SignalOutputValidationError(f"invalid JSON: {path}") from e
    if not isinstance(x,dict): raise SignalOutputValidationError("top-level JSON must be object")
    return x

def validate_config(c:Dict[str,Any])->None:
    if c.get("validation_scope")!="OFFLINE_PAPER_SIGNAL_OUTPUT_ONLY":
        raise SignalOutputValidationError("validation_scope invalid")
    if c.get("expected_signal_method")!="SIMPLE_MOVING_AVERAGE_CROSSOVER":
        raise SignalOutputValidationError("expected_signal_method invalid")
    for k in ("require_execution_integrity","require_signal_package_integrity","require_consumed_token",
              "require_signal_id_recalculation","require_sma_recalculation","require_zero_orders",
              "require_network_disabled"):
        if c.get(k) is not True: raise SignalOutputValidationError(f"{k} must be true")
    for k in ("order_generation_allowed","fill_simulation_allowed","paper_orders_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed"):
        if c.get(k) is not False: raise SignalOutputValidationError(f"{k} must be false")

def validate_source(s:Dict[str,Any])->None:
    if s.get("status")!="PASS": raise SignalOutputValidationError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA: raise SignalOutputValidationError("unsupported source schema")
    if s.get("execution_state")!="READY_FOR_SIGNAL_OUTPUT_VALIDATION":
        raise SignalOutputValidationError("source not ready for output validation")
    observed=s.get("offline_paper_signal_generation_execution_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_signal_generation_execution_sha256",None)
    if observed!=sha256_of(clone): raise SignalOutputValidationError("execution integrity failed")
    for field in ("execution_checks","execution_ledger","consumed_authorization_token","signal_output_package"):
        hash_field={
            "execution_checks":"execution_checks_sha256",
            "execution_ledger":"execution_ledger_sha256",
            "consumed_authorization_token":"consumed_authorization_token_sha256",
            "signal_output_package":"signal_output_package_sha256",
        }[field]
        if s.get(hash_field)!=sha256_of(s.get(field)):
            raise SignalOutputValidationError(f"{field} integrity failed")
    if s.get("authorization_state")!="CONSUMED" or s.get("token_consumed") is not True:
        raise SignalOutputValidationError("authorization token must be consumed")
    token=s.get("consumed_authorization_token")
    if not isinstance(token,dict) or token.get("consumed") is not True or token.get("token_state")!="CONSUMED":
        raise SignalOutputValidationError("consumed token invalid")
    if token.get("single_use") is not True or not token.get("consumed_at"):
        raise SignalOutputValidationError("single-use token consumption evidence invalid")
    if s.get("signal_generation_executed") is not True:
        raise SignalOutputValidationError("signal generation not executed")
    gate=s.get("execution_gate",{})
    expected={"signal_generation_executed":True,"signal_output_validation_allowed":True,
              "order_generation_allowed":False,"fill_simulation_allowed":False,
              "paper_orders_allowed":False,"live_orders_allowed":False,
              "network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise SignalOutputValidationError(f"execution_gate {k} invalid")
    for k in ("order_generation_allowed","fill_simulation_allowed","paper_orders_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed"):
        if s.get(k) is not False: raise SignalOutputValidationError(f"{k} must be false")
    if s.get("orders_created")!=0 or s.get("orders_submitted")!=0:
        raise SignalOutputValidationError("order side effects detected")
    if s.get("approved_for_live") is not False or s.get("network_used") is not False:
        raise SignalOutputValidationError("live/network safety violation")

def signal_material(sig:Dict[str,Any])->Dict[str,Any]:
    return {k:sig[k] for k in ("symbol","as_of","strategy_id","signal_method","price_field",
                                "fast_window","slow_window","fast_sma","slow_sma","latest_price","action")}

def validate_signal_package(s:Dict[str,Any])->Dict[str,Any]:
    pkg=s["signal_output_package"]
    if pkg.get("immutable") is not True or pkg.get("network_source") is not False:
        raise SignalOutputValidationError("signal package must be immutable offline data")
    if pkg.get("orders_created")!=0 or pkg.get("orders_submitted")!=0:
        raise SignalOutputValidationError("signal package contains order side effects")
    for k in ("authorization_id","validation_id","preparation_id","session_id","cycle_id",
              "cycle_sequence","champion_candidate_id","signal_execution_id"):
        if pkg.get(k)!=s.get(k): raise SignalOutputValidationError(f"{k} mismatch")
    signals=pkg.get("signals")
    summary=pkg.get("signal_summary")
    if not isinstance(signals,list) or not signals: raise SignalOutputValidationError("signals required")
    if not isinstance(summary,dict): raise SignalOutputValidationError("signal_summary required")
    actions={"BUY":0,"SELL":0,"HOLD":0}
    symbols=[]
    for sig in signals:
        if sig.get("signal_method")!="SIMPLE_MOVING_AVERAGE_CROSSOVER":
            raise SignalOutputValidationError("signal method invalid")
        fw,sw=sig.get("fast_window"),sig.get("slow_window")
        if not isinstance(fw,int) or not isinstance(sw,int) or fw<=0 or sw<=fw:
            raise SignalOutputValidationError("signal windows invalid")
        fast=float(sig["fast_sma"]); slow=float(sig["slow_sma"])
        expected="BUY" if fast>slow else "SELL" if fast<slow else "HOLD"
        if sig.get("action")!=expected: raise SignalOutputValidationError("signal action inconsistent with SMA")
        expected_id="SIG-"+sha256_of(signal_material(sig))[:16].upper()
        if sig.get("signal_id")!=expected_id: raise SignalOutputValidationError("signal_id mismatch")
        if sig.get("order_created") is not False or sig.get("order_submitted") is not False:
            raise SignalOutputValidationError("signal has order side effect")
        actions[expected]+=1; symbols.append(sig["symbol"])
    expected_summary={"signal_count":len(signals),"buy_count":actions["BUY"],"sell_count":actions["SELL"],
                      "hold_count":actions["HOLD"],"symbols":symbols,
                      "strategy_id":signals[0]["strategy_id"],
                      "signal_method":"SIMPLE_MOVING_AVERAGE_CROSSOVER"}
    if summary!=expected_summary: raise SignalOutputValidationError("signal_summary mismatch")
    return pkg

def validation_id(signal_execution_id:str,validated_at:str)->str:
    return "SOV-"+hashlib.sha256(f"{signal_execution_id}|{validated_at}|{VERSION}".encode()).hexdigest()[:16].upper()

def build_validation(source:Dict[str,Any],config:Dict[str,Any],validated_at:str)->Dict[str,Any]:
    validate_config(config); validate_source(source); pkg=validate_signal_package(source)
    vid=validation_id(source["signal_execution_id"],validated_at)
    checks=[
      {"check_index":1,"check":"SIGNAL_GENERATION_EXECUTION_INTEGRITY","state":"PASS"},
      {"check_index":2,"check":"SIGNAL_OUTPUT_PACKAGE_INTEGRITY","state":"PASS"},
      {"check_index":3,"check":"CONSUMED_TOKEN_EVIDENCE","state":"PASS"},
      {"check_index":4,"check":"SIGNAL_COUNT_CONSISTENCY","state":"PASS"},
      {"check_index":5,"check":"SIGNAL_SUMMARY_CONSISTENCY","state":"PASS"},
      {"check_index":6,"check":"SMA_RELATIONSHIP_VALID","state":"PASS"},
      {"check_index":7,"check":"SIGNAL_ACTION_VALID","state":"PASS"},
      {"check_index":8,"check":"SIGNAL_ID_RECALCULATION","state":"PASS"},
      {"check_index":9,"check":"ORDER_GENERATION_NOT_STARTED","state":"PASS"},
      {"check_index":10,"check":"ZERO_ORDER_SIDE_EFFECTS","state":"PASS"},
      {"check_index":11,"check":"NETWORK_DISABLED","state":"PASS"},
      {"check_index":12,"check":"LIVE_TRADING_PROHIBITION","state":"ENFORCED"},
    ]
    ledger=[
      {"ledger_index":1,"event":"SIGNAL_EXECUTION_VERIFIED","state":"PASS","validation_id":vid},
      {"ledger_index":2,"event":"SIGNAL_PACKAGE_VERIFIED","state":"PASS","validation_id":vid},
      {"ledger_index":3,"event":"SIGNALS_RECALCULATED","state":"PASS","validation_id":vid},
      {"ledger_index":4,"event":"SIGNAL_IDENTITIES_VERIFIED","state":"PASS","validation_id":vid},
      {"ledger_index":5,"event":"SAFETY_LOCKS_RECONFIRMED","state":"ENFORCED","validation_id":vid},
      {"ledger_index":6,"event":"SIGNAL_OUTPUT_VALIDATION_COMPLETED","state":"READY_FOR_ORDER_INTENT_AUTHORIZATION","validation_id":vid},
    ]
    out={
      "status":"PASS","decision":"offline_paper_signal_output_validated",
      "validation_id":vid,"validation_state":"READY_FOR_ORDER_INTENT_AUTHORIZATION",
      "signal_execution_id":source["signal_execution_id"],
      "authorization_id":source["authorization_id"],"session_id":source["session_id"],
      "cycle_id":source["cycle_id"],"cycle_sequence":source["cycle_sequence"],
      "champion_candidate_id":source["champion_candidate_id"],
      "validated_signal_summary":copy.deepcopy(pkg["signal_summary"]),
      "validated_signals":copy.deepcopy(pkg["signals"]),
      "validation_checks":checks,"validation_checks_sha256":sha256_of(checks),
      "validation_ledger":ledger,"validation_ledger_sha256":sha256_of(ledger),
      "source_signal_generation_execution_sha256":source["offline_paper_signal_generation_execution_sha256"],
      "source_signal_output_package_sha256":source["signal_output_package_sha256"],
      "validation_gate":{"signal_output_validated":True,"order_intent_authorization_allowed":True,
                         "order_generation_allowed":False,"fill_simulation_allowed":False,
                         "paper_orders_allowed":False,"live_orders_allowed":False,
                         "network_allowed":False,"next_version":"75.2Q"},
      "order_generation_allowed":False,"fill_simulation_allowed":False,
      "paper_orders_allowed":False,"live_orders_allowed":False,
      "network_allowed":False,"broker_connection_allowed":False,
      "orders_created":0,"orders_submitted":0,"approved_for_live":False,"network_used":False,
      "safety_lock":copy.deepcopy(source["safety_lock"]),
      "validated_at":validated_at,"schema_version":SCHEMA,"version":VERSION
    }
    out["offline_paper_signal_output_validation_sha256"]=sha256_of(out)
    return out

def write_outputs(out:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_signal_output_validation_v75_2p.json":out,
      "offline_paper_signal_output_validation_checks_v75_2p.json":{"validation_id":out["validation_id"],"validation_checks":out["validation_checks"],"validation_checks_sha256":out["validation_checks_sha256"]},
      "offline_paper_signal_output_validation_ledger_v75_2p.json":{"validation_id":out["validation_id"],"validation_ledger":out["validation_ledger"],"validation_ledger_sha256":out["validation_ledger_sha256"]},
      "offline_paper_validated_signals_v75_2p.json":{"validation_id":out["validation_id"],"validated_signal_summary":out["validated_signal_summary"],"validated_signals":out["validated_signals"]}
    }
    for name,p in payloads.items():
        (d/name).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_signal_output_validation_v75_2p.sha256").write_text(out["offline_paper_signal_output_validation_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--validated-at")
    a=p.parse_args(argv)
    try:
        import datetime
        ts=a.validated_at or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
        out=build_validation(read_json(Path(a.input)),read_json(Path(a.config)),ts)
        write_outputs(out,Path(a.output_dir))
        print(json.dumps({"status":out["status"],"decision":out["decision"],
          "validation_id":out["validation_id"],"validation_state":out["validation_state"],
          **out["validated_signal_summary"],
          "order_intent_authorization_allowed":out["validation_gate"]["order_intent_authorization_allowed"],
          "order_generation_allowed":False,"orders_created":0,"orders_submitted":0,
          "network_allowed":False,"approved_for_live":False,"network_used":False,
          "offline_paper_signal_output_validation_sha256":out["offline_paper_signal_output_validation_sha256"]},indent=2,sort_keys=True))
        return 0
    except (SignalOutputValidationError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_signal_output_validation_failed",
          "error":str(e),"approved_for_live":False,"network_used":False,
          "orders_created":0,"orders_submitted":0,"version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__": raise SystemExit(main())
