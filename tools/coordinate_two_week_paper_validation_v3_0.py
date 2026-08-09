from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse, json, subprocess, sys

ET=ZoneInfo("America/New_York")
STATE_REL=Path("runtime/paper_2week_validation_v3_0/state.json")
REPORT_REL=Path("runtime/paper_2week_validation_v3_0/latest_validation_report.json")
HOOK_LEDGER_REL=Path("runtime/regime_aware_buy_shadow_v2_8_1/hook_ledger.jsonl")
SESSION_LEDGER_REL=Path("runtime/paper_autonomous_daily_session/session_ledger.jsonl")
V294_REPORT_REL=Path("runtime/regime_aware_buy_shadow_v2_9_4/latest_runtime_observation_gate_v2_9_4.json")
V294_TOOL_REL=Path("tools/certify_runtime_observation_gate_v2_9_4.py")

REQUIRED_GATE_HOOKS=3
REQUIRED_TRADING_DAYS=10
MIN_SUCCESSFUL_HOOKS_PER_DAY=3


def read_jsonl(path:Path):
    if not path.exists():
        return []
    rows=[]
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append({"_parse_error":True,"_raw":line[:500]})
    return rows


def parse_dt(value):
    if not value:
        return None
    try:
        dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def et_date(value):
    dt=parse_dt(value)
    return dt.astimezone(ET).date().isoformat() if dt else None


def ensure_gate(root:Path):
    tool=root/V294_TOOL_REL
    if not tool.exists():
        raise RuntimeError(f"V2.9.4 gate tool missing: {tool}")
    p=subprocess.run(
        [sys.executable,str(tool),"--root",str(root)],
        cwd=root,capture_output=True,text=True,errors="replace",check=False
    )
    report_path=root/V294_REPORT_REL
    if not report_path.exists():
        raise RuntimeError(
            "V2.9.4 report missing after gate execution; "
            f"exit={p.returncode}; stderr={p.stderr[-2000:]}"
        )
    return json.loads(report_path.read_text(encoding="utf-8-sig"))


def load_state(root:Path):
    p=root/STATE_REL
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(root:Path,state):
    p=root/STATE_REL
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(state,indent=2),encoding="utf-8")


def main_run(root:Path):
    root=root.resolve()
    gate=ensure_gate(root)
    successful_gate_hooks=int(gate.get("successful_hook_count",0) or 0)

    hooks=read_jsonl(root/HOOK_LEDGER_REL)
    sessions=read_jsonl(root/SESSION_LEDGER_REL)
    hook_parse_errors=sum(1 for r in hooks if r.get("_parse_error"))
    blocked_count=sum(1 for r in hooks if r.get("primary_paper_flow_blocked") is True)
    live_submit_count=sum(1 for r in hooks if r.get("live_order_submission_performed") is True)

    pass_hooks=[r for r in hooks if r.get("status")=="PASS"]
    pass_dates=Counter()
    for r in pass_hooks:
        d=et_date(r.get("timestamp_utc"))
        if d:
            pass_dates[d]+=1

    eligible_dates=sorted(
        d for d,count in pass_dates.items()
        if count>=MIN_SUCCESSFUL_HOOKS_PER_DAY
    )

    state=load_state(root)
    state_created=False

    if successful_gate_hooks>=REQUIRED_GATE_HOOKS and state is None:
        # Start only when the already-existing runtime gate has actually passed.
        start_date=eligible_dates[0] if eligible_dates else None
        state={
            "stage":"V3.0_TWO_WEEK_PAPER_VALIDATION_STATE",
            "created_at_utc":datetime.now(timezone.utc).isoformat(),
            "gate_passed_at_creation":True,
            "validation_start_trading_date":start_date,
            "required_trading_days":REQUIRED_TRADING_DAYS,
            "minimum_successful_hooks_per_day":MIN_SUCCESSFUL_HOOKS_PER_DAY,
            "production_parameters_frozen_by_coordinator":False,
            "automatic_promotion":False,
        }
        save_state(root,state)
        state_created=True

    start_date=state.get("validation_start_trading_date") if state else None
    counted_dates=[
        d for d in eligible_dates
        if start_date is not None and d>=start_date
    ]
    counted_dates=counted_dates[:REQUIRED_TRADING_DAYS]

    isolated_failures=sum(
        1 for r in hooks
        if r.get("status") in {
            "SHADOW_NONZERO_ISOLATED",
            "SHADOW_TIMEOUT_ISOLATED",
            "SHADOW_EXCEPTION_ISOLATED",
        }
    )

    structural_ok=(
        hook_parse_errors==0
        and blocked_count==0
        and live_submit_count==0
    )

    if successful_gate_hooks<REQUIRED_GATE_HOOKS:
        status="PASS_WAITING_FOR_RUNTIME_GATE"
    elif not structural_ok:
        status="BLOCKED_TWO_WEEK_VALIDATION_INTEGRITY"
    elif start_date is None:
        status="PASS_GATE_MET_WAITING_FOR_FIRST_ELIGIBLE_TRADING_DAY"
    elif len(counted_dates)>=REQUIRED_TRADING_DAYS:
        status="PASS_TWO_WEEK_PAPER_VALIDATION"
    else:
        status="PASS_TWO_WEEK_VALIDATION_ACTIVE"

    stage_counts=Counter(str(r.get("stage","UNKNOWN")) for r in sessions)
    report={
        "stage":"V3.0_TWO_WEEK_PAPER_VALIDATION_COORDINATOR",
        "status":status,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "reused_components":[
            "tools/certify_runtime_observation_gate_v2_9_4.py",
            "runtime/regime_aware_buy_shadow_v2_8_1/hook_ledger.jsonl",
            "runtime/paper_autonomous_daily_session/session_ledger.jsonl",
        ],
        "runtime_gate":{
            "v2_9_4_status":gate.get("status"),
            "successful_hook_count":successful_gate_hooks,
            "required_successful_hooks":REQUIRED_GATE_HOOKS,
            "gate_passed":successful_gate_hooks>=REQUIRED_GATE_HOOKS,
        },
        "validation_state":{
            "state_exists":state is not None,
            "state_created_this_run":state_created,
            "validation_start_trading_date":start_date,
            "required_trading_days":REQUIRED_TRADING_DAYS,
            "completed_trading_days":len(counted_dates),
            "remaining_trading_days":max(0,REQUIRED_TRADING_DAYS-len(counted_dates)),
            "counted_trading_dates":counted_dates,
            "eligible_trading_dates_seen":eligible_dates,
            "minimum_successful_hooks_per_day":MIN_SUCCESSFUL_HOOKS_PER_DAY,
        },
        "hook_integrity":{
            "ledger_exists":(root/HOOK_LEDGER_REL).exists(),
            "record_count":len(hooks),
            "pass_count":len(pass_hooks),
            "isolated_failure_count":isolated_failures,
            "parse_error_count":hook_parse_errors,
            "primary_paper_flow_blocked_true_count":blocked_count,
            "live_order_submission_true_count":live_submit_count,
            "successful_hooks_by_et_date":dict(sorted(pass_dates.items())),
        },
        "paper_session_observation":{
            "ledger_exists":(root/SESSION_LEDGER_REL).exists(),
            "record_count":len(sessions),
            "latest_stage":sessions[-1].get("stage") if sessions else None,
            "stage_counts":dict(stage_counts),
        },
        "contracts":{
            "duplicate_trading_engine_created":False,
            "paper_runtime_modified":False,
            "scheduled_task_modified":False,
            "paper_runtime_started_by_v3_0":False,
            "broker_write_performed_by_v3_0":False,
            "paper_order_submission_performed_by_v3_0":False,
            "live_order_submission_performed_by_v3_0":False,
            "production_parameter_modified":False,
            "production_selector_modified":False,
            "automatic_promotion":False,
        },
    }

    out=root/REPORT_REL
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    return 2 if status.startswith("BLOCKED") else 0


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    return main_run(Path(a.root))


if __name__=="__main__":
    raise SystemExit(main())
