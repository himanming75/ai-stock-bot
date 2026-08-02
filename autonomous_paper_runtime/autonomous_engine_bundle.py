from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _load(path: Path) -> dict[str, Any]:
    if not path.exists(): return {}
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(f"JSON object required: {path}")
    return value

def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    tmp.replace(path)

def _id(prefix: str,*parts: str)->str:
    return prefix+hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]

class AutonomousEngineBundle:
    def run(self,*,control_result_path:Path,control_token_path:Path,signal_path:Path,
            account_path:Path,recovery_path:Path,scheduler_path:Path,
            order_candidate_path:Path,recovery_token_path:Path,
            heartbeat_path:Path,engine_token_path:Path,result_path:Path)->dict[str,Any]:
        issues=[]
        try: control=_load(control_result_path)
        except Exception as exc:
            control={}; issues.append({"code":"INVALID_CONTROL_RESULT","blocking":True,"detail":str(exc)})
        if not control:
            issues.append({"code":"CONTROL_RESULT_NOT_FOUND","blocking":True,"detail":str(control_result_path)})
        ready=bool(control.get("runtime_control_ready",False))
        state=str(control.get("state","")).upper()
        status=str(control.get("status","")).upper()
        safe=bool(control.get("safe_mode_engaged",False))
        runtime_cycle_id=str(control.get("runtime_cycle_id","")).strip()
        if safe or status=="BLOCKED":
            issues.append({"code":"SOURCE_CONTROL_SAFE_MODE","blocking":True,"detail":state})
        required=ready or state=="RUNTIME_CONTROL_READY"
        token=signal=account=recovery=scheduler={}
        if required:
            for name,path in (("CONTROL_TOKEN",control_token_path),("SIGNAL",signal_path),
                              ("ACCOUNT",account_path),("RECOVERY",recovery_path),("SCHEDULER",scheduler_path)):
                try: loaded=_load(path)
                except Exception as exc:
                    loaded={}; issues.append({"code":f"INVALID_{name}","blocking":True,"detail":str(exc)})
                if not loaded:
                    issues.append({"code":f"{name}_NOT_FOUND","blocking":True,"detail":str(path)})
                if name=="CONTROL_TOKEN": token=loaded
                elif name=="SIGNAL": signal=loaded
                elif name=="ACCOUNT": account=loaded
                elif name=="RECOVERY": recovery=loaded
                else: scheduler=loaded
        if token and (token.get("runtime_cycle_id")!=runtime_cycle_id or not token.get("runtime_control_ready",False)):
            issues.append({"code":"CONTROL_TOKEN_MISMATCH","blocking":True,"detail":"runtime cycle mismatch"})
        signal_ready=False; quantity=0
        if signal:
            side=str(signal.get("side","")).upper()
            confidence=float(signal.get("confidence",0) or 0)
            entry=float(signal.get("entry_price",0) or 0)
            stop=float(signal.get("stop_price",0) or 0)
            if side not in {"BUY","SELL"}: issues.append({"code":"INVALID_SIGNAL_SIDE","blocking":True,"detail":side})
            if confidence < float(signal.get("minimum_confidence",0.7)): issues.append({"code":"LOW_SIGNAL_CONFIDENCE","blocking":True,"detail":str(confidence)})
            if entry<=0 or stop<=0 or entry==stop: issues.append({"code":"INVALID_SIGNAL_PRICES","blocking":True,"detail":"entry/stop"})
            signal_ready=not any(i["code"].startswith(("INVALID_SIGNAL","LOW_SIGNAL")) for i in issues)
        sizing_ready=False
        if account and signal_ready:
            equity=float(account.get("equity",0) or 0); buying=float(account.get("buying_power",0) or 0)
            risk_pct=float(account.get("risk_per_trade_pct",0.005) or 0.005)
            max_exp=float(account.get("max_symbol_exposure",0) or 0)
            entry=float(signal["entry_price"]); stop=float(signal["stop_price"])
            risk_dollars=max(equity*risk_pct,0); per_share=abs(entry-stop)
            quantity=int(risk_dollars//per_share) if per_share>0 else 0
            quantity=min(quantity,int(buying//entry),int(max_exp//entry) if max_exp>0 else quantity)
            if quantity<=0: issues.append({"code":"POSITION_SIZE_ZERO","blocking":True,"detail":"calculated quantity <= 0"})
            sizing_ready=quantity>0
        recovery_ready=False
        if recovery:
            checks=[
                ("UNRESOLVED_SUBMISSION",not bool(recovery.get("unresolved_submission",False))),
                ("ACTIVE_ORDER_PRESENT",not bool(recovery.get("active_order_present",False))),
                ("STATE_CORRUPTED",not bool(recovery.get("state_corrupted",False))),
                ("RECOVERY_NOT_VERIFIED",bool(recovery.get("recovery_verified",False))),
            ]
            for code,passed in checks:
                if not passed: issues.append({"code":code,"blocking":True,"detail":"crash recovery gate failed"})
            recovery_ready=all(p for _,p in checks)
        scheduler_ready=False
        if scheduler:
            checks=[
                ("SCHEDULER_DISABLED",bool(scheduler.get("enabled",False))),
                ("INVALID_INTERVAL",int(scheduler.get("interval_seconds",0))>=5),
                ("STALE_SCHEDULER_HEARTBEAT",int(scheduler.get("heartbeat_age_seconds",999999))<=int(scheduler.get("max_heartbeat_age_seconds",120))),
                ("DUPLICATE_SCHEDULER",int(scheduler.get("scheduler_process_count",0))<=1),
            ]
            for code,passed in checks:
                if not passed: issues.append({"code":code,"blocking":True,"detail":"scheduler gate failed"})
            scheduler_ready=all(p for _,p in checks)
        blocking=sum(1 for i in issues if i.get("blocking"))
        safe_mode=blocking>0
        candidate_written=recovery_written=heartbeat_written=engine_written=False
        engine_ready=bool(required and token and signal_ready and sizing_ready and recovery_ready and scheduler_ready and not safe_mode)
        engine_id=_id("engine-",runtime_cycle_id,str(signal.get("signal_id","")),str(quantity)) if engine_ready else ""
        if engine_ready:
            candidate={"engine_id":engine_id,"runtime_cycle_id":runtime_cycle_id,"signal_id":signal.get("signal_id",""),
                       "symbol":str(signal.get("symbol","")).upper(),"side":str(signal.get("side","")).upper(),
                       "quantity":quantity,"order_type":"MARKET","risk_approved":True,
                       "created_at":datetime.now(timezone.utc).isoformat()}
            _write(order_candidate_path,candidate); candidate_written=True
            _write(recovery_token_path,{"engine_id":engine_id,"recovery_verified":True,"created_at":datetime.now(timezone.utc).isoformat()}); recovery_written=True
            _write(heartbeat_path,{"engine_id":engine_id,"heartbeat_at":datetime.now(timezone.utc).isoformat(),
                                   "interval_seconds":scheduler.get("interval_seconds")}); heartbeat_written=True
            token_payload={"engine_id":engine_id,"runtime_cycle_id":runtime_cycle_id,"autonomous_engine_ready":True,
                           "actual_submission_allowed":False,"broker_network_allowed":False,
                           "created_at":datetime.now(timezone.utc).isoformat()}
            if engine_token_path.exists():
                existing=_load(engine_token_path)
                if existing.get("engine_id")!=engine_id:
                    issues.append({"code":"ENGINE_TOKEN_CONFLICT","blocking":True,"detail":"another engine identity exists"})
                else: engine_written=True
            else:
                _write(engine_token_path,token_payload); engine_written=True
        blocking=sum(1 for i in issues if i.get("blocking")); safe_mode=blocking>0
        engine_ready=bool(engine_ready and engine_written and not safe_mode)
        if safe_mode: out_state,out_status="AUTONOMOUS_ENGINE_SAFE_MODE","BLOCKED"
        elif engine_ready: out_state,out_status="AUTONOMOUS_ENGINE_READY","PASS"
        else: out_state,out_status="WAIT_RUNTIME_CONTROL","PASS"
        result={"stage_range":"V140.06-V140.09","implementation_type":"ULTRA_FAST_AUTONOMOUS_ENGINE_BUNDLE",
                "status":out_status,"state":out_state,"runtime_cycle_id":runtime_cycle_id,"engine_id":engine_id,
                "signal_ready":signal_ready,"position_sizing_ready":sizing_ready,"calculated_quantity":quantity,
                "crash_recovery_ready":recovery_ready,"scheduler_ready":scheduler_ready,
                "order_candidate_written":candidate_written,"recovery_token_written":recovery_written,
                "heartbeat_written":heartbeat_written,"autonomous_engine_ready":engine_ready,
                "safe_mode_engaged":safe_mode,"issue_count":len(issues),"blocking_issue_count":blocking,"issues":issues,
                "next_phase":"V140_10_TO_V140_12" if engine_ready else "V140_06_TO_V140_09_WAIT_RUNTIME_CONTROL",
                "actual_credentials_used":False,"actual_external_network_used":False,"network_requests_executed":0,
                "write_requests_executed":0,"actual_paper_orders_submitted":0,"live_orders_submitted":0,
                "validation_mode":"LOCAL_AUTONOMOUS_ENGINE_ONLY","observed_at":datetime.now(timezone.utc).isoformat(),
                "result_path":str(result_path.resolve())}
        _write(result_path,result); return result
