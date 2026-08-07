from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, subprocess

TASK_STATE_MAP = {0:"Unknown",1:"Disabled",2:"Queued",3:"Ready",4:"Running"}

def read_json(path: Path):
    try:
        x=json.loads(path.read_text(encoding="utf-8-sig"))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}

def normalize_state(value):
    if value is None:
        return None
    if isinstance(value,bool):
        return str(value)
    if isinstance(value,(int,float)):
        return TASK_STATE_MAP.get(int(value),str(int(value)))
    s=str(value).strip()
    if s.isdigit():
        return TASK_STATE_MAP.get(int(s),s)
    known={x.lower():x for x in TASK_STATE_MAP.values()}
    return known.get(s.lower(),s)

def task_state(name: str):
    ps = f'''
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
}} | ConvertTo-Json -Compress
'''
    try:
        p=subprocess.run(
            ["powershell.exe","-NoProfile","-Command",ps],
            capture_output=True,text=True,encoding="utf-8",errors="replace"
        )
        if p.returncode!=0 or not p.stdout.strip():
            return {"task_name":name,"exists":False,"state":None,"state_value":None}
        x=json.loads(p.stdout.strip())
        return {
            "task_name":name,"exists":True,
            "state":normalize_state(x.get("State")),
            "state_value":x.get("StateValue"),
            "last_run_time":x.get("LastRunTime"),
            "last_task_result":x.get("LastTaskResult"),
            "next_run_time":x.get("NextRunTime"),
        }
    except Exception as exc:
        return {"task_name":name,"exists":None,"state":None,"state_value":None,"error":str(exc)}

def _first_report(root: Path, paths):
    for rel in paths:
        x=read_json(root/rel)
        if x:
            x["_source"]=rel
            return x
    return {}

def build(root: Path):
    root=Path(root)
    paper=task_state("AIStockBot-PaperAutonomousDailySession")
    finalizer=task_state("AIStockBot-PaperValidationFinalizeStart")
    research=task_state("AIStockBot-AIResearchShadow")
    observer_task=task_state("AIStockBot-PaperValidationObserver")

    validation=read_json(root/"runtime/paper_backtest_validation_analytics_v3/latest_validation_analytics.json")
    lr=validation.get("live_readiness",{}) if isinstance(validation,dict) else {}
    closed=int(lr.get("observed_closed_trades",0) or 0)
    days=int(lr.get("observed_trading_days",0) or 0)

    flat_report=_first_report(root,[
        "runtime/paper_validation_2week_300/latest_flatten_status.json",
        "runtime/paper_validation_2week_300/finalizer_status.json",
        "runtime/paper_validation_2week_300/latest_finalize_status.json",
        "runtime/paper_validation_2week_300/latest_status.json",
        "runtime/paper_validation_finalize/latest_status.json",
        "runtime/paper_validation_finalize/latest_finalize_status.json",
    ])

    paper_state=normalize_state(paper.get("state"))
    finalizer_state=normalize_state(finalizer.get("state"))
    research_state=normalize_state(research.get("state"))

    transition={
        "finalizer_ready_or_running": finalizer_state in ("Ready","Running"),
        "paper_task_ready_or_running": paper_state in ("Ready","Running"),
        "paper_task_disabled": paper_state=="Disabled",
        "research_task_ready_or_running": research_state in ("Ready","Running"),
        "flat_status_observed": flat_report.get("status"),
        "flat_report_source": flat_report.get("_source"),
        "position_count_observed": flat_report.get("remaining_position_count",flat_report.get("position_count")),
        "open_order_count_observed": flat_report.get("remaining_open_order_count",flat_report.get("open_order_count")),
    }

    if transition["paper_task_ready_or_running"]:
        state="PAPER_AUTONOMOUS_ENABLED"
    elif transition["paper_task_disabled"] and transition["finalizer_ready_or_running"]:
        state="WAITING_FOR_FINALIZER_FLAT_CONFIRMATION"
    elif paper.get("exists") is False:
        state="PAPER_TASK_MISSING"
    elif finalizer.get("exists") is False:
        state="FINALIZER_TASK_MISSING"
    else:
        state="REVIEW_TASK_STATE"

    progress={
        "closed_trades":closed,
        "target_closed_trades":300,
        "closed_trade_progress_pct":round(min(100.0,closed/300*100),2),
        "trading_days":days,
        "target_trading_days":10,
        "trading_day_progress_pct":round(min(100.0,days/10*100),2),
    }

    report={
        "stage":"PAPER_VALIDATION_TRANSITION_OBSERVER_V2",
        "status":"PASS",
        "mode":"READ_ONLY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "paper_task":paper,
        "finalizer_task":finalizer,
        "ai_research_task":research,
        "observer_task":observer_task,
        "transition_state":state,
        "transition_observation":transition,
        "validation_progress":progress,
        "contracts":{
            "task_changes_performed_by_observer":False,
            "broker_write_performed":False,
            "paper_order_submitted":False,
            "live_order_submitted":False,
            "trading_configuration_changed":False,
            "strategy_parameter_changed":False,
        },
    }

    out=root/"runtime/paper_validation_transition_observer"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_transition_observer.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    with (out/"transition_observer_ledger.jsonl").open("a",encoding="utf-8") as h:
        h.write(json.dumps(report,default=str)+"\n")
    return report

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"C:\stock-bot")
    args=ap.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
