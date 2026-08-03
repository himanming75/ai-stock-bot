from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_ACTION = "SUPERVISED_TRIGGER_REENTRY"

def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}

def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")

def guard_id(approval_id: str, observed_at: str) -> str:
    raw = f"{approval_id}|{observed_at}".encode("utf-8")
    return "reentry-guard-" + hashlib.sha256(raw).hexdigest()[:20]

def run_reentry_execution_guard_audit(
    *, approval_result_path: Path, approval_lock_path: Path,
    reentry_plan_path: Path, retry_plan_path: Path, retry_lock_path: Path,
    policy_path: Path, execution_lock_path: Path, audit_ledger_path: Path,
    execution_plan_path: Path, recovery_snapshot_path: Path,
    dashboard_path: Path, result_path: Path,
    prepare_execution: bool=False, dry_run: bool=True,
    clear_execution_lock: bool=False, observed_at_override: str=""
) -> dict[str, Any]:
    observed = datetime.fromisoformat(observed_at_override) if observed_at_override else datetime.now(timezone.utc)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    observed_iso = observed.isoformat()
    issues = []
    inputs = {}
    for name, path in {
        "approval_result": approval_result_path, "approval_lock": approval_lock_path,
        "reentry_plan": reentry_plan_path, "retry_plan": retry_plan_path,
        "retry_lock": retry_lock_path, "policy": policy_path,
    }.items():
        try:
            inputs[name] = load_json(path)
        except Exception as exc:
            inputs[name] = {}
            issues.append({"code": f"INVALID_{name.upper()}", "blocking": True, "detail": str(exc)})

    policy = inputs["policy"]
    if not policy:
        issues.append({"code":"REENTRY_GUARD_POLICY_NOT_FOUND","blocking":True,"detail":str(policy_path)})

    for code, passed in (
        ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
        ("BROKER_WRITE_MUST_BE_DISABLED", not bool(policy.get("broker_write_enabled", True))),
        ("ORDER_SUBMISSION_MUST_BE_DISABLED", not bool(policy.get("order_submission_enabled", True))),
        ("LIVE_TRADING_MUST_BE_DISABLED", not bool(policy.get("live_trading_enabled", True))),
        ("EXTERNAL_NETWORK_MUST_BE_DISABLED", not bool(policy.get("external_network_enabled", True))),
        ("AUTOMATIC_EXECUTION_MUST_BE_DISABLED", not bool(policy.get("automatic_execution_enabled", True))),
    ):
        if not passed:
            issues.append({"code":code,"blocking":True,"detail":"re-entry guard safety policy failed"})

    approval_result=inputs["approval_result"]; approval_lock=inputs["approval_lock"]
    reentry_plan=inputs["reentry_plan"]; retry_plan=inputs["retry_plan"]; retry_lock=inputs["retry_lock"]
    existing_lock=load_json(execution_lock_path)
    duplicate=prepare_execution and bool(existing_lock.get("active",False))
    if duplicate:
        issues.append({"code":"DUPLICATE_REENTRY_EXECUTION_BLOCKED","blocking":True,"detail":str(existing_lock.get("guard_id",""))})

    state="REENTRY_EXECUTION_GUARD_WAIT_APPROVAL"; status="PASS"
    current_guard_id=str(existing_lock.get("guard_id",""))
    guard_written=plan_written=audit_written=recovery_written=False

    if any(i.get("blocking") for i in issues):
        state="REENTRY_EXECUTION_GUARD_SAFE_MODE"; status="BLOCKED"
    elif clear_execution_lock:
        write_json(execution_lock_path,{"active":False,"guard_id":"","cleared_at":observed_iso,"paper_only":True})
        state="REENTRY_EXECUTION_LOCK_CLEARED"
    elif prepare_execution:
        for name,value in {
            "APPROVAL_RESULT":approval_result,"APPROVAL_LOCK":approval_lock,
            "REENTRY_PLAN":reentry_plan,"RETRY_PLAN":retry_plan,"RETRY_LOCK":retry_lock
        }.items():
            if not value:
                issues.append({"code":f"{name}_NOT_FOUND","blocking":True,"detail":""})
        if approval_result and approval_result.get("state")!="SUPERVISED_REENTRY_READY":
            issues.append({"code":"APPROVAL_RESULT_NOT_READY","blocking":True,"detail":str(approval_result.get("state",""))})
        if approval_lock and not bool(approval_lock.get("active",False)):
            issues.append({"code":"APPROVAL_LOCK_NOT_ACTIVE","blocking":True,"detail":str(approval_lock.get("approval_id",""))})
        expires_at=str(approval_lock.get("expires_at",""))
        if expires_at:
            expires=datetime.fromisoformat(expires_at)
            if expires.tzinfo is None:
                expires=expires.replace(tzinfo=timezone.utc)
            if observed>expires:
                issues.append({"code":"REENTRY_APPROVAL_EXPIRED","blocking":True,"detail":expires_at})
        approval_ids={
            str(approval_result.get("approval_id","")),
            str(approval_lock.get("approval_id","")),
            str(reentry_plan.get("approval_id","")),
        } - {""}
        if len(approval_ids)>1:
            issues.append({"code":"APPROVAL_ID_MISMATCH","blocking":True,"detail":sorted(approval_ids)})
        retry_ids={
            str(retry_plan.get("retry_plan_id","")),
            str(retry_lock.get("retry_plan_id","")),
            str(approval_lock.get("retry_plan_id","")),
            str(reentry_plan.get("retry_plan_id","")),
        } - {""}
        if len(retry_ids)>1:
            issues.append({"code":"RETRY_PLAN_ID_MISMATCH","blocking":True,"detail":sorted(retry_ids)})
        if reentry_plan and reentry_plan.get("action")!=ALLOWED_ACTION:
            issues.append({"code":"DISALLOWED_REENTRY_ACTION","blocking":True,"detail":str(reentry_plan.get("action",""))})
        if retry_lock and not bool(retry_lock.get("active",False)):
            issues.append({"code":"RETRY_LOCK_NOT_ACTIVE","blocking":True,"detail":str(retry_lock.get("retry_plan_id",""))})

        if any(i.get("blocking") for i in issues):
            state="REENTRY_EXECUTION_GUARD_SAFE_MODE"; status="BLOCKED"
            write_json(recovery_snapshot_path,{
                "stage":"V83.47","state":"REENTRY_EXECUTION_GUARD_RECOVERY_REQUIRED",
                "issues":issues,"captured_at":observed_iso,"paper_only":True})
            recovery_written=True
        else:
            approval_id=str(approval_lock.get("approval_id",""))
            retry_plan_id=str(retry_plan.get("retry_plan_id",""))
            current_guard_id=guard_id(approval_id,observed_iso)
            write_json(execution_lock_path,{
                "active":True,"guard_id":current_guard_id,"approval_id":approval_id,
                "retry_plan_id":retry_plan_id,"created_at":observed_iso,"paper_only":True})
            guard_written=True
            plan={
                "stage":"V83.46","state":"REENTRY_EXECUTION_DRY_RUN_READY",
                "guard_id":current_guard_id,"approval_id":approval_id,
                "retry_plan_id":retry_plan_id,"trigger_id":str(retry_plan.get("trigger_id","")),
                "action":"RUN_SUPERVISED_REENTRY_RUNNER","dry_run":dry_run,
                "automatic_execution_enabled":False,"operator_confirmation_required":True,
                "paper_only":True,"created_at":observed_iso}
            write_json(execution_plan_path,plan); plan_written=True
            append_jsonl(audit_ledger_path,{**plan,"event":"REENTRY_EXECUTION_GUARD_PASSED"}); audit_written=True
            state="REENTRY_EXECUTION_DRY_RUN_READY" if dry_run else "REENTRY_EXECUTION_SUPERVISED_READY"
    elif bool(existing_lock.get("active",False)):
        state="REENTRY_EXECUTION_GUARD_ACTIVE"

    dashboard={
        "stage":"V83.48","state":state,"status":status,
        "reentry_execution_guard_state":state,"guard_id":current_guard_id,
        "prepare_execution_requested":prepare_execution,"dry_run":dry_run,
        "duplicate_execution":duplicate,"guard_written":guard_written,
        "execution_plan_written":plan_written,"audit_written":audit_written,
        "recovery_snapshot_written":recovery_written,
        "operator_supervision_required":True,"automatic_execution_enabled":False,
        "broker_write_enabled":False,"order_submission_enabled":False,
        "live_trading_enabled":False,"external_network_enabled":False,
        "actual_paper_orders_submitted":0,"live_orders_submitted":0,
        "paper_only":True,"observed_at":observed_iso}
    write_json(dashboard_path,dashboard)
    result={**dashboard,"stage_range":"V83.45-V83.48",
        "implementation_type":"REENTRY_EXECUTION_GUARD_AND_AUDIT",
        "actual_credentials_used":False,"actual_external_network_used":False,
        "network_requests_executed":0,"write_requests_executed":0,
        "broker_command_execution_enabled":False,
        "issue_count":len(issues),"blocking_issue_count":sum(1 for i in issues if i.get("blocking")),
        "issues":issues,
        "next_phase":"V83_49_SUPERVISED_REENTRY_RUNNER_INTEGRATION" if status=="PASS" else "V83_45_TO_V83_48_RECOVER",
        "validation_mode":"LOCAL_REENTRY_GUARD_AND_AUDIT_ONLY",
        "result_path":str(result_path.resolve())}
    write_json(result_path,result)
    return result
