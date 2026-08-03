from __future__ import annotations
import hashlib, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict[str, Any]:
    if not path.exists(): return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}

def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as s:
        s.write(json.dumps(payload, sort_keys=True) + "\n")

def approval_id(retry_plan_id: str, observed_at: str) -> str:
    raw = f"{retry_plan_id}|{observed_at}".encode()
    return "retry-approval-" + hashlib.sha256(raw).hexdigest()[:20]

def run_retry_approval_supervised_reentry(
    *, retry_policy_result_path: Path, retry_plan_path: Path,
    retry_lock_path: Path, approval_policy_path: Path,
    approval_lock_path: Path, approval_ledger_path: Path,
    reentry_plan_path: Path, dashboard_path: Path, result_path: Path,
    approve_retry: bool=False, complete_reentry: bool=False,
    clear_approval_lock: bool=False, observed_at_override: str=""
) -> dict[str, Any]:
    observed_at = datetime.fromisoformat(observed_at_override) if observed_at_override else datetime.now(timezone.utc)
    if observed_at.tzinfo is None: observed_at = observed_at.replace(tzinfo=timezone.utc)
    now = observed_at.isoformat()
    issues=[]
    try: retry_result=load_json(retry_policy_result_path)
    except Exception as e: retry_result={}; issues.append({"code":"INVALID_RETRY_RESULT","blocking":True,"detail":str(e)})
    try: retry_plan=load_json(retry_plan_path)
    except Exception as e: retry_plan={}; issues.append({"code":"INVALID_RETRY_PLAN","blocking":True,"detail":str(e)})
    try: retry_lock=load_json(retry_lock_path)
    except Exception as e: retry_lock={}; issues.append({"code":"INVALID_RETRY_LOCK","blocking":True,"detail":str(e)})
    try: policy=load_json(approval_policy_path)
    except Exception as e: policy={}; issues.append({"code":"INVALID_APPROVAL_POLICY","blocking":True,"detail":str(e)})

    if not policy:
        issues.append({"code":"APPROVAL_POLICY_NOT_FOUND","blocking":True,"detail":str(approval_policy_path)})

    checks=(
        ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only",False))),
        ("BROKER_WRITE_MUST_BE_DISABLED", not bool(policy.get("broker_write_enabled",True))),
        ("ORDER_SUBMISSION_MUST_BE_DISABLED", not bool(policy.get("order_submission_enabled",True))),
        ("LIVE_TRADING_MUST_BE_DISABLED", not bool(policy.get("live_trading_enabled",True))),
        ("EXTERNAL_NETWORK_MUST_BE_DISABLED", not bool(policy.get("external_network_enabled",True))),
        ("AUTOMATIC_REENTRY_MUST_BE_DISABLED", not bool(policy.get("automatic_reentry_execution_enabled",True))),
    )
    for code, passed in checks:
        if not passed: issues.append({"code":code,"blocking":True,"detail":"approval safety policy failed"})

    approval_lock=load_json(approval_lock_path)
    duplicate=approve_retry and bool(approval_lock.get("active",False))
    if duplicate:
        issues.append({"code":"DUPLICATE_RETRY_APPROVAL_BLOCKED","blocking":True,"detail":str(approval_lock.get("approval_id",""))})

    state="RETRY_APPROVAL_WAIT_PLAN"; status="PASS"
    current_id=str(approval_lock.get("approval_id",""))
    approval_written=False; reentry_plan_written=False; reentry_completed=False

    if any(i.get("blocking") for i in issues):
        state="RETRY_APPROVAL_SAFE_MODE"
        status="BLOCKED"

    elif clear_approval_lock:
        write_json(approval_lock_path,{"active":False,"approval_id":"","cleared_at":now,"paper_only":True})
        state="RETRY_APPROVAL_LOCK_CLEARED"

    elif approve_retry:
        if retry_result.get("state") != "TRIGGER_RETRY_PLANNED":
            issues.append({"code":"RETRY_NOT_IN_PLANNED_STATE","blocking":True,"detail":str(retry_result.get("state",""))})
        if not retry_plan:
            issues.append({"code":"RETRY_PLAN_NOT_FOUND","blocking":True,"detail":str(retry_plan_path)})
        if not bool(retry_lock.get("active",False)):
            issues.append({"code":"RETRY_LOCK_NOT_ACTIVE","blocking":True,"detail":str(retry_lock_path)})
        if retry_plan and str(retry_lock.get("retry_plan_id","")) != str(retry_plan.get("retry_plan_id","")):
            issues.append({"code":"RETRY_PLAN_LOCK_ID_MISMATCH","blocking":True,"detail":str(retry_plan.get("retry_plan_id",""))})

        if any(i.get("blocking") for i in issues):
            state="RETRY_APPROVAL_SAFE_MODE"; status="BLOCKED"
        else:
            ttl=int(policy.get("approval_ttl_seconds",900) or 900)
            expires=(observed_at+timedelta(seconds=ttl)).isoformat()
            current_id=approval_id(str(retry_plan["retry_plan_id"]),now)
            write_json(approval_lock_path,{
                "active":True,"approval_id":current_id,
                "retry_plan_id":retry_plan["retry_plan_id"],
                "trigger_id":retry_plan.get("trigger_id",""),
                "approved_at":now,"expires_at":expires,"paper_only":True
            })
            reentry={
                "stage":"V83.43","state":"SUPERVISED_REENTRY_READY",
                "approval_id":current_id,"retry_plan_id":retry_plan["retry_plan_id"],
                "trigger_id":retry_plan.get("trigger_id",""),
                "action":"SUPERVISED_TRIGGER_REENTRY",
                "automatic_reentry_execution_enabled":False,
                "operator_confirmation_required":True,
                "expires_at":expires,"paper_only":True
            }
            write_json(reentry_plan_path,reentry)
            append_jsonl(approval_ledger_path,{**reentry,"event":"RETRY_APPROVED_FOR_SUPERVISED_REENTRY","approved_at":now})
            approval_written=True; reentry_plan_written=True; state="SUPERVISED_REENTRY_READY"

    elif complete_reentry:
        if bool(approval_lock.get("active",False)):
            expires=str(approval_lock.get("expires_at",""))
            expired=bool(expires and observed_at > datetime.fromisoformat(expires))
            if expired:
                issues.append({"code":"RETRY_APPROVAL_EXPIRED","blocking":True,"detail":expires})
                state="RETRY_APPROVAL_EXPIRED"; status="BLOCKED"
            else:
                done=datetime.now(timezone.utc).isoformat()
                write_json(approval_lock_path,{
                    "active":False,"approval_id":approval_lock.get("approval_id",""),
                    "retry_plan_id":approval_lock.get("retry_plan_id",""),
                    "completed_at":done,"paper_only":True
                })
                append_jsonl(approval_ledger_path,{
                    "stage":"V83.43","event":"SUPERVISED_REENTRY_COMPLETED",
                    "approval_id":approval_lock.get("approval_id",""),
                    "retry_plan_id":approval_lock.get("retry_plan_id",""),
                    "completed_at":done,"paper_only":True
                })
                reentry_completed=True; state="SUPERVISED_REENTRY_COMPLETED"
        else:
            state="NO_ACTIVE_RETRY_APPROVAL"

    elif bool(approval_lock.get("active",False)):
        expires=str(approval_lock.get("expires_at",""))
        if expires and observed_at > datetime.fromisoformat(expires):
            state="RETRY_APPROVAL_EXPIRED"
        else:
            state="SUPERVISED_REENTRY_READY"

    dashboard={
        "stage":"V83.44","state":state,"status":status,
        "retry_approval_state":state,"approval_id":current_id,
        "retry_plan_id":str(retry_plan.get("retry_plan_id","")),
        "approval_written":approval_written,
        "reentry_plan_written":reentry_plan_written,
        "reentry_completed":reentry_completed,
        "operator_supervision_required":True,
        "automatic_reentry_execution_enabled":False,
        "broker_write_enabled":False,"order_submission_enabled":False,
        "live_trading_enabled":False,"external_network_enabled":False,
        "actual_paper_orders_submitted":0,"live_orders_submitted":0,
        "paper_only":True,"observed_at":now
    }
    write_json(dashboard_path,dashboard)
    result={**dashboard,
        "stage_range":"V83.41-V83.44",
        "implementation_type":"RETRY_APPROVAL_AND_SUPERVISED_REENTRY",
        "duplicate_approval":duplicate,
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "network_requests_executed":0,"write_requests_executed":0,
        "issue_count":len(issues),
        "blocking_issue_count":sum(1 for i in issues if i.get("blocking")),
        "issues":issues,
        "next_phase":"V83_45_REENTRY_EXECUTION_GUARD_AND_AUDIT" if status=="PASS" else "V83_41_TO_V83_44_RECOVER",
        "validation_mode":"LOCAL_APPROVAL_AND_REENTRY_PLANNING_ONLY",
        "result_path":str(result_path.resolve())
    }
    write_json(result_path,result)
    return result
