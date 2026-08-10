from __future__ import annotations
from pathlib import Path
from typing import Any
from datetime import datetime
import json
import os
import socket

def _read_json(path:Path)->dict[str,Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig",errors="replace"))
    except Exception:
        return {}

def _write_json(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True,default=str),encoding="utf-8")
    os.replace(tmp,path)

def _port_open(port:int)->bool:
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(0.25)
    try:
        return s.connect_ex(("127.0.0.1",port))==0
    finally:
        s.close()

def _validation_payload(root:Path)->dict[str,Any]:
    try:
        from web_controller.validation_lab_api import get_payload
        return get_payload(root)
    except Exception as exc:
        return {"error":f"{type(exc).__name__}: {exc}"}

def _scheduler(root:Path)->dict[str,Any]:
    try:
        from validation_automation.scheduler import scheduler_status
        return scheduler_status(root)
    except Exception as exc:
        return {"running":False,"error":f"{type(exc).__name__}: {exc}"}

def _ops_dir(root:Path)->Path:
    p=root/"runtime/daily_operations_center"
    p.mkdir(parents=True,exist_ok=True)
    return p

def _checks(root:Path,validation:dict[str,Any],scheduler:dict[str,Any])->list[dict[str,Any]]:
    progress=validation.get("progress") or {}
    finalq=validation.get("final_qualification") or {}
    safety=validation.get("safety") or {}
    rows=[
        {"check":"CONTROL_CENTER_8770","passed":_port_open(8770),"detail":"127.0.0.1:8770"},
        {"check":"VALIDATION_API_AVAILABLE","passed":"error" not in validation,"detail":validation.get("error","OK")},
        {"check":"VALIDATION_SCHEDULER_RUNNING","passed":bool(scheduler.get("running")),"detail":scheduler.get("pid")},
        {"check":"NO_VALIDATION_LIVE_ORDERS","passed":int(safety.get("live_orders_submitted_by_validation_lab") or 0)==0,"detail":safety.get("live_orders_submitted_by_validation_lab",0)},
        {"check":"NO_VALIDATION_PAPER_ORDERS","passed":int(safety.get("paper_orders_submitted_by_validation_lab") or 0)==0,"detail":safety.get("paper_orders_submitted_by_validation_lab",0)},
        {"check":"NO_AUTOMATIC_PROMOTION","passed":not bool(finalq.get("automatic_promotion")),"detail":finalq.get("automatic_promotion",False)},
        {"check":"NO_SYNTHETIC_PROGRESS","passed":not bool(progress.get("synthetic_progress_used")),"detail":progress.get("synthetic_progress_used",False)},
        {"check":"NO_FABRICATED_FUTURE_OUTCOMES","passed":not bool(progress.get("future_outcomes_fabricated")),"detail":progress.get("future_outcomes_fabricated",False)},
    ]
    return rows

def _today_action(validation:dict[str,Any],scheduler:dict[str,Any])->dict[str,Any]:
    progress=validation.get("progress") or {}
    finalq=validation.get("final_qualification") or {}
    decision=finalq.get("decision","CONTINUE")
    if decision=="FAIL":
        state="ACTION_REQUIRED"
        action="STOP_AND_REVIEW_FINAL_QUALIFICATION_FAILURE"
    elif decision=="PASS":
        state="READY_FOR_MANUAL_REVIEW"
        action="MANUAL_PROMOTION_REVIEW"
    elif not scheduler.get("running"):
        state="ACTION_REQUIRED"
        action="START_VALIDATION_SCHEDULER"
    else:
        state="WAITING"
        action=progress.get("next_milestone","CONTINUE_VALIDATION")
    return {
        "state":state,
        "action":action,
        "final_qualification_decision":decision,
        "next_milestone":progress.get("next_milestone"),
        "blockers":progress.get("blockers",[]),
    }

def get_payload(root:Path)->dict[str,Any]:
    validation=_validation_payload(root)
    scheduler=_scheduler(root)
    progress=validation.get("progress") or {}
    finalq=validation.get("final_qualification") or {}
    checks=_checks(root,validation,scheduler)
    hard_fail=any((not r["passed"]) for r in checks if r["check"] in {
        "NO_VALIDATION_LIVE_ORDERS","NO_VALIDATION_PAPER_ORDERS",
        "NO_AUTOMATIC_PROMOTION","NO_SYNTHETIC_PROGRESS",
        "NO_FABRICATED_FUTURE_OUTCOMES"
    })
    system_state="BLOCKED" if hard_fail else "READY"

    latest=_read_json(_ops_dir(root)/"latest_operations_snapshot.json")
    return {
        "system":{
            "state":system_state,
            "control_center":"RUNNING" if _port_open(8770) else "STOPPED",
            "control_center_port":8770,
            "etrade":"DEFERRED",
            "paper_execution_change_from_daily_ops":False,
            "live_execution_change_from_daily_ops":False,
        },
        "validation":{
            "days_completed":progress.get("trading_days_completed",0),
            "days_target":progress.get("trading_days_target",10),
            "resolved_outcomes":progress.get("resolved_outcomes",0),
            "resolved_target":progress.get("resolved_outcomes_target",200),
            "waiting_for_future_marks":progress.get("waiting_for_future_marks",0),
            "ai_health":progress.get("ai_health","NOT_AVAILABLE"),
            "paper_qualified":progress.get("paper_qualified",False),
            "final_decision":finalq.get("decision","CONTINUE"),
        },
        "scheduler":scheduler,
        "checks":checks,
        "today_action":_today_action(validation,scheduler),
        "latest_snapshot":latest,
        "safety":{
            "etrade_used":False,
            "broker_network_used_by_daily_ops":False,
            "paper_engine_started_by_daily_ops":False,
            "paper_orders_submitted_by_daily_ops":0,
            "live_orders_submitted_by_daily_ops":0,
            "automatic_strategy_change":False,
            "automatic_threshold_change":False,
            "automatic_model_promotion":False,
            "live_trading_enabled":False,
        },
    }

def _save_snapshot(root:Path)->dict[str,Any]:
    payload=get_payload(root)
    snap={
        "captured_at_local":datetime.now().astimezone().isoformat(),
        "system":payload["system"],
        "validation":payload["validation"],
        "scheduler":{
            "running":payload["scheduler"].get("running",False),
            "pid":payload["scheduler"].get("pid"),
            "last_run":payload["scheduler"].get("last_run",{}),
        },
        "today_action":payload["today_action"],
        "checks":payload["checks"],
        "safety":payload["safety"],
    }
    out=_ops_dir(root)
    ts=datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    path=out/f"operations_snapshot_{ts}.json"
    _write_json(path,snap)
    _write_json(out/"latest_operations_snapshot.json",snap)
    return {"ok":True,"path":str(path.relative_to(root)).replace("\\","/"),"snapshot":snap}

def action_payload(root:Path,body:dict[str,Any])->dict[str,Any]:
    action=str(body.get("action",""))
    if action=="run_daily_check":
        p=get_payload(root)
        return {
            "ok":True,
            "action":action,
            "system":p["system"],
            "validation":p["validation"],
            "today_action":p["today_action"],
            "checks":p["checks"],
            "safety":p["safety"],
        }
    if action=="save_operations_snapshot":
        return _save_snapshot(root)
    if action=="start_validation_scheduler":
        try:
            from validation_automation.scheduler import start_scheduler
            return {"action":action,**start_scheduler(root)}
        except Exception as exc:
            return {"ok":False,"action":action,"error":f"{type(exc).__name__}: {exc}"}
    if action=="stop_validation_scheduler":
        try:
            from validation_automation.scheduler import stop_scheduler
            return {"action":action,**stop_scheduler(root)}
        except Exception as exc:
            return {"ok":False,"action":action,"error":f"{type(exc).__name__}: {exc}"}
    return {"ok":False,"action":action,"error":"ACTION_NOT_ALLOWED"}
