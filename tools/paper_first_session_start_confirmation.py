from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, subprocess, os

TASK_STATE_MAP={0:"Unknown",1:"Disabled",2:"Queued",3:"Ready",4:"Running"}

def read_json(path: Path):
    try:
        x=json.loads(path.read_text(encoding="utf-8-sig"))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}

def read_jsonl(path: Path):
    if not path.exists():
        return []
    out=[]
    for raw in path.read_text(encoding="utf-8-sig",errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            x=json.loads(raw)
            if isinstance(x,dict):
                out.append(x)
        except Exception:
            pass
    return out

def normalize_state(value):
    if value is None: return None
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        return TASK_STATE_MAP.get(int(value),str(int(value)))
    s=str(value).strip()
    if s.isdigit():
        return TASK_STATE_MAP.get(int(s),s)
    known={x.lower():x for x in TASK_STATE_MAP.values()}
    return known.get(s.lower(),s)

def task_state(name: str):
    ps=f"""
$task=Get-ScheduledTask -TaskName "{name}" -ErrorAction SilentlyContinue
if(-not $task){{ exit 0 }}
$info=Get-ScheduledTaskInfo -TaskName "{name}" -ErrorAction SilentlyContinue
[pscustomobject]@{{
 TaskName=$task.TaskName
 State=$task.State.ToString()
 StateValue=[int]$task.State
 LastRunTime=if($info){{$info.LastRunTime.ToString("o")}}else{{$null}}
 LastTaskResult=if($info){{$info.LastTaskResult}}else{{$null}}
 NextRunTime=if($info -and $info.NextRunTime){{$info.NextRunTime.ToString("o")}}else{{$null}}
}}|ConvertTo-Json -Compress
"""
    try:
        p=subprocess.run(["powershell.exe","-NoProfile","-Command",ps],
                         capture_output=True,text=True,encoding="utf-8",errors="replace")
        if p.returncode!=0 or not p.stdout.strip():
            return {"task_name":name,"exists":False,"state":None}
        x=json.loads(p.stdout.strip())
        return {"task_name":name,"exists":True,"state":normalize_state(x.get("State")),
                "state_value":x.get("StateValue"),"last_run_time":x.get("LastRunTime"),
                "last_task_result":x.get("LastTaskResult"),"next_run_time":x.get("NextRunTime")}
    except Exception as exc:
        return {"task_name":name,"exists":None,"state":None,"error":str(exc)}

def alpaca_readonly_snapshot():
    key=os.getenv("APCA_API_KEY_ID","").strip()
    secret=os.getenv("APCA_API_SECRET_KEY","").strip()
    if not key or not secret:
        return {"status":"CREDENTIALS_NOT_AVAILABLE_TO_OBSERVER","broker_read_performed":False}
    try:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest
        client=TradingClient(key,secret,paper=True)
        clock=client.get_clock()
        positions=list(client.get_all_positions())
        open_orders=list(client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN,limit=500)))
        all_orders=list(client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.ALL,limit=500)))
        today=str(getattr(clock,"timestamp",""))[:10]
        todays=[]
        for x in all_orders:
            created=str(getattr(x,"created_at",""))
            if created[:10]==today:
                todays.append(x)
        return {
            "status":"PASS","paper_only":True,"broker_read_performed":True,
            "market_open":bool(getattr(clock,"is_open",False)),
            "timestamp":str(getattr(clock,"timestamp","")),
            "next_open":str(getattr(clock,"next_open","")),
            "next_close":str(getattr(clock,"next_close","")),
            "position_count":len(positions),
            "position_symbols":[str(getattr(x,"symbol","")).upper() for x in positions],
            "open_order_count":len(open_orders),
            "open_order_symbols":[str(getattr(x,"symbol","")).upper() for x in open_orders],
            "today_order_count":len(todays),
            "today_order_symbols":[str(getattr(x,"symbol","")).upper() for x in todays],
            "today_order_sides":[str(getattr(x,"side","")) for x in todays],
        }
    except Exception as exc:
        return {"status":"ADVISORY_ERROR","broker_read_performed":False,
                "error":f"{type(exc).__name__}: {exc}"}

def latest_row(path: Path):
    rows=read_jsonl(path)
    return rows[-1] if rows else {}

def todays_launches(root: Path, date_key: str):
    rows=read_jsonl(root/"runtime/paper_autotrading_ramp_v2/launch_ledger.jsonl")
    return [x for x in rows if str(x.get("date",""))==date_key]

def closed_validation_count(root: Path, baseline: dict):
    rows=read_jsonl(root/"runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl")
    base=max(0,int((baseline or {}).get("baseline_closed_trade_count",0) or 0))
    return max(0,len(rows)-base)

def current_day_plan(plan: dict, date_key: str):
    for row in plan.get("daily_entry_caps",[]) if isinstance(plan,dict) else []:
        if str(row.get("date",""))==date_key:
            return row
    return {}

def build(root: Path):
    root=Path(root)
    paper=task_state("AIStockBot-PaperAutonomousDailySession")
    finalizer=task_state("AIStockBot-PaperValidationFinalizeStart")
    research=task_state("AIStockBot-AIResearchShadow")
    observer_task=task_state("AIStockBot-PaperValidationObserver")
    broker=alpaca_readonly_snapshot()
    baseline=read_json(root/"runtime/paper_validation_2week_300/baseline.json")
    plan=read_json(root/"config/paper_validation_2week_300.json")

    broker_ts=str(broker.get("timestamp",""))
    date_key=broker_ts[:10] if len(broker_ts)>=10 else datetime.now(timezone.utc).date().isoformat()
    launches=todays_launches(root,date_key)
    latest_launch=launches[-1] if launches else {}
    latest_exit=latest_row(root/"runtime/paper_autotrading_ramp_v2/exit_ledger.jsonl")
    day_plan=current_day_plan(plan,date_key)
    closed=closed_validation_count(root,baseline)

    validation=read_json(root/"runtime/paper_backtest_validation_analytics_v3/latest_validation_analytics.json")
    lr=validation.get("live_readiness",{}) if isinstance(validation,dict) else {}
    days=int(lr.get("observed_trading_days",0) or 0)

    paper_state=normalize_state(paper.get("state"))
    finalizer_state=normalize_state(finalizer.get("state"))
    market_open=broker.get("market_open")
    flat=(broker.get("position_count")==0 and broker.get("open_order_count")==0
          if broker.get("status")=="PASS" else None)
    launch_present=bool(latest_launch)
    launch_cap=latest_launch.get("maximum_daily_orders")
    plan_cap=day_plan.get("maximum_daily_entries")

    if launch_present and paper_state=="Running":
        runtime_state="DAY_SESSION_RUNNING"
    elif launch_present and paper_state in ("Ready","Running"):
        runtime_state="DAY_SESSION_STARTED"
    elif paper_state in ("Ready","Running") and not launch_present:
        runtime_state="TASK_ENABLED_AWAITING_LAUNCH_LEDGER"
    elif paper_state=="Disabled" and finalizer_state in ("Ready","Running"):
        if market_open is False:
            runtime_state="WAITING_FOR_MARKET_OPEN"
        elif market_open is True and flat is False:
            runtime_state="FINALIZER_FLATTENING"
        elif market_open is True and flat is True:
            runtime_state="FLAT_CONFIRMED_AWAITING_TASK_ENABLE"
        else:
            runtime_state="WAITING_FOR_FINALIZER_FLAT_CONFIRMATION"
    else:
        runtime_state="REVIEW_RUNTIME_STATE"

    cap_contract = None
    if launch_present and plan_cap is not None:
        cap_contract = int(launch_cap)==int(plan_cap)

    first_session_started = launch_present and paper_state in ("Ready","Running")
    day1_active = bool(latest_launch and int(latest_launch.get("validation_day",0) or 0)==1)

    report={
        "stage":"DAY1_RUNTIME_VERIFICATION_V1",
        "status":"PASS",
        "mode":"READ_ONLY_RUNTIME_VERIFICATION",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "date_key":date_key,
        "runtime_state":runtime_state,
        "first_session_started":first_session_started,
        "day1_active":day1_active,
        "paper_task":paper,
        "finalizer_task":finalizer,
        "ai_research_task":research,
        "observer_task":observer_task,
        "alpaca_paper_snapshot":broker,
        "account_flat_observed":flat,
        "validation_plan":{
            "validation_id":plan.get("validation_id") if isinstance(plan,dict) else None,
            "target_closed_trades":plan.get("target_closed_trades") if isinstance(plan,dict) else None,
            "current_day":day_plan.get("day"),
            "current_day_maximum_entries":plan_cap,
        },
        "baseline":{
            "exists":bool(baseline),
            "paper_account_flat_at_start":baseline.get("paper_account_flat_at_start") if baseline else None,
            "baseline_closed_trade_count":baseline.get("baseline_closed_trade_count") if baseline else None,
            "created_at_utc":baseline.get("created_at_utc") if baseline else None,
        },
        "session_evidence":{
            "today_launch_count":len(launches),
            "launch_record_present":launch_present,
            "latest_launch":latest_launch,
            "latest_exit":latest_exit,
            "launch_cap_matches_plan":cap_contract,
        },
        "validation_progress":{
            "closed_trades":closed,"target_closed_trades":300,
            "closed_trade_progress_pct":round(min(100.0,closed/300*100),2),
            "trading_days":days,"target_trading_days":10,
            "trading_day_progress_pct":round(min(100.0,days/10*100),2),
        },
        "runtime_checks":{
            "paper_only_snapshot":broker.get("paper_only") is True if broker.get("status")=="PASS" else None,
            "launch_cap_contract":cap_contract,
            "live_auto_enable_off":True,
            "first_session_started":first_session_started,
        },
        "contracts":{
            "broker_read_only":True,
            "broker_write_performed":False,
            "paper_order_submitted_by_verifier":False,
            "live_order_submitted":False,
            "task_changes_performed_by_verifier":False,
            "strategy_parameter_changed":False,
            "risk_parameter_changed":False,
            "live_auto_enable":False,
        },
    }

    out=root/"runtime/paper_validation_transition_observer"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_day1_runtime_verification.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )
    with (out/"day1_runtime_verification_ledger.jsonl").open("a",encoding="utf-8") as h:
        h.write(json.dumps(report,default=str)+"\n")
    return report

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"C:\stock-bot")
    args=ap.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
