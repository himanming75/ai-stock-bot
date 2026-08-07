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
    if s.isdigit(): return TASK_STATE_MAP.get(int(s),s)
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
        orders=list(client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN,limit=500)))
        return {
            "status":"PASS","paper_only":True,"broker_read_performed":True,
            "market_open":bool(getattr(clock,"is_open",False)),
            "timestamp":str(getattr(clock,"timestamp","")),
            "next_open":str(getattr(clock,"next_open","")),
            "next_close":str(getattr(clock,"next_close","")),
            "position_count":len(positions),
            "position_symbols":[str(getattr(x,"symbol","")).upper() for x in positions],
            "open_order_count":len(orders),
            "open_order_symbols":[str(getattr(x,"symbol","")).upper() for x in orders],
        }
    except Exception as exc:
        return {"status":"ADVISORY_ERROR","broker_read_performed":False,
                "error":f"{type(exc).__name__}: {exc}"}

def latest_launch(root: Path):
    rows=read_jsonl(root/"runtime/paper_autotrading_ramp_v2/launch_ledger.jsonl")
    return rows[-1] if rows else {}

def latest_exit(root: Path):
    rows=read_jsonl(root/"runtime/paper_autotrading_ramp_v2/exit_ledger.jsonl")
    return rows[-1] if rows else {}

def build(root: Path):
    root=Path(root)
    paper=task_state("AIStockBot-PaperAutonomousDailySession")
    finalizer=task_state("AIStockBot-PaperValidationFinalizeStart")
    research=task_state("AIStockBot-AIResearchShadow")
    observer_task=task_state("AIStockBot-PaperValidationObserver")
    broker=alpaca_readonly_snapshot()
    baseline=read_json(root/"runtime/paper_validation_2week_300/baseline.json")
    plan=read_json(root/"config/paper_validation_2week_300.json")
    launch=latest_launch(root)
    exitrow=latest_exit(root)

    validation=read_json(root/"runtime/paper_backtest_validation_analytics_v3/latest_validation_analytics.json")
    lr=validation.get("live_readiness",{}) if isinstance(validation,dict) else {}
    closed=int(lr.get("observed_closed_trades",0) or 0)
    days=int(lr.get("observed_trading_days",0) or 0)

    paper_state=normalize_state(paper.get("state"))
    finalizer_state=normalize_state(finalizer.get("state"))
    market_open=broker.get("market_open")
    flat=(broker.get("position_count")==0 and broker.get("open_order_count")==0
          if broker.get("status")=="PASS" else None)

    if paper_state in ("Ready","Running"):
        startup="FIRST_SESSION_LAUNCHED" if launch else "PAPER_TASK_ENABLED_AWAITING_SESSION_EVIDENCE"
    elif paper_state=="Disabled" and finalizer_state in ("Ready","Running"):
        if market_open is False:
            startup="WAITING_FOR_MARKET_OPEN"
        elif market_open is True and flat is False:
            startup="FINALIZER_FLATTENING"
        elif market_open is True and flat is True:
            startup="FLAT_CONFIRMED_AWAITING_TASK_ENABLE"
        else:
            startup="WAITING_FOR_FINALIZER_FLAT_CONFIRMATION"
    else:
        startup="REVIEW_STARTUP_STATE"

    day1=None
    for row in plan.get("daily_entry_caps",[]) if isinstance(plan,dict) else []:
        if int(row.get("day",0) or 0)==1:
            day1=row
            break

    report={
        "stage":"PAPER_FIRST_SESSION_START_CONFIRMATION_V1",
        "status":"PASS","mode":"READ_ONLY_CONFIRMATION",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "startup_state":startup,
        "paper_task":paper,"finalizer_task":finalizer,
        "ai_research_task":research,"observer_task":observer_task,
        "alpaca_paper_snapshot":broker,
        "account_flat_observed":flat,
        "validation_plan":{
            "validation_id":plan.get("validation_id") if isinstance(plan,dict) else None,
            "target_closed_trades":plan.get("target_closed_trades") if isinstance(plan,dict) else None,
            "day1_maximum_entries":day1.get("maximum_daily_entries") if day1 else None,
        },
        "baseline":{
            "exists":bool(baseline),
            "paper_account_flat_at_start":baseline.get("paper_account_flat_at_start") if baseline else None,
            "baseline_closed_trade_count":baseline.get("baseline_closed_trade_count") if baseline else None,
            "created_at_utc":baseline.get("created_at_utc") if baseline else None,
        },
        "session_evidence":{"launch_record_present":bool(launch),"latest_launch":launch,"latest_exit":exitrow},
        "validation_progress":{"closed_trades":closed,"target_closed_trades":300,
                               "trading_days":days,"target_trading_days":10},
        "contracts":{"broker_read_only":True,"broker_write_performed":False,
                     "paper_order_submitted_by_observer":False,"live_order_submitted":False,
                     "task_changes_performed_by_observer":False,"strategy_parameter_changed":False,
                     "live_auto_enable":False},
    }
    out=root/"runtime/paper_validation_transition_observer"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_start_confirmation.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    with (out/"start_confirmation_ledger.jsonl").open("a",encoding="utf-8") as h:
        h.write(json.dumps(report,default=str)+"\n")
    return report

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"C:\stock-bot")
    args=ap.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
