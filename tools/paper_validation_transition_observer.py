from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, subprocess

def read_json(path: Path):
    try:
        x=json.loads(path.read_text(encoding="utf-8-sig"))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}

def task_state(name: str):
    ps = (
        "Get-ScheduledTask -TaskName "
        + repr(name)
        + " -ErrorAction SilentlyContinue | "
          "Select-Object TaskName,State | ConvertTo-Json -Compress"
    )
    try:
        p=subprocess.run(
            ["powershell.exe","-NoProfile","-Command",ps],
            capture_output=True,text=True,encoding="utf-8",errors="replace"
        )
        if p.returncode!=0 or not p.stdout.strip():
            return {"task_name":name,"exists":False,"state":None}
        x=json.loads(p.stdout.strip())
        return {"task_name":name,"exists":True,"state":x.get("State")}
    except Exception as exc:
        return {"task_name":name,"exists":None,"state":None,"error":str(exc)}

def build(root: Path):
    root=Path(root)
    paper=task_state("AIStockBot-PaperAutonomousDailySession")
    finalizer=task_state("AIStockBot-PaperValidationFinalizeStart")
    research=task_state("AIStockBot-AIResearchShadow")

    validation=read_json(
        root/"runtime/paper_backtest_validation_analytics_v3/latest_validation_analytics.json"
    )
    lr=validation.get("live_readiness",{}) if isinstance(validation,dict) else {}
    closed=int(lr.get("observed_closed_trades",0) or 0)
    days=int(lr.get("observed_trading_days",0) or 0)

    flat_report=read_json(root/"runtime/paper_validation_2week_300/latest_flatten_status.json")
    # Fall back to other likely existing finalizer/flatten reports, read-only.
    if not flat_report:
        for p in [
            root/"runtime/paper_validation_2week_300/finalizer_status.json",
            root/"runtime/paper_validation_2week_300/latest_finalize_status.json",
            root/"runtime/paper_validation_2week_300/latest_status.json",
        ]:
            flat_report=read_json(p)
            if flat_report: break

    transition={
        "finalizer_ready": finalizer.get("state")=="Ready",
        "paper_task_ready_or_running": paper.get("state") in ("Ready","Running"),
        "paper_task_disabled": paper.get("state")=="Disabled",
        "flat_status_observed": flat_report.get("status"),
        "position_count_observed": flat_report.get("remaining_position_count", flat_report.get("position_count")),
        "open_order_count_observed": flat_report.get("remaining_open_order_count", flat_report.get("open_order_count")),
    }

    if transition["paper_task_ready_or_running"]:
        state="PAPER_AUTONOMOUS_ENABLED"
    elif transition["paper_task_disabled"] and transition["finalizer_ready"]:
        state="WAITING_FOR_FINALIZER_FLAT_CONFIRMATION"
    else:
        state="REVIEW_TASK_STATE"

    report={
        "stage":"PAPER_VALIDATION_TRANSITION_OBSERVER",
        "status":"PASS",
        "mode":"READ_ONLY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "paper_task":paper,
        "finalizer_task":finalizer,
        "ai_research_task":research,
        "transition_state":state,
        "transition_observation":transition,
        "validation_progress":{
            "closed_trades":closed,
            "target_closed_trades":300,
            "closed_trade_progress_pct":round(min(100.0,closed/300*100),2),
            "trading_days":days,
            "target_trading_days":10,
            "trading_day_progress_pct":round(min(100.0,days/10*100),2),
        },
        "contracts":{
            "task_changes_performed":False,
            "broker_write_performed":False,
            "paper_order_submitted":False,
            "live_order_submitted":False,
            "trading_configuration_changed":False,
        },
    }

    out=root/"runtime/paper_validation_transition_observer"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_transition_observer.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )
    return report

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"C:\stock-bot")
    args=ap.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
