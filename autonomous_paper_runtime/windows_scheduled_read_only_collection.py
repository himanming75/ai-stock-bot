from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


class WindowsScheduledReadOnlyCollection:
    def run(
        self,
        *,
        collector_result_path: Path,
        schedule_policy_path: Path,
        recovery_snapshot_path: Path,
        task_plan_path: Path,
        heartbeat_path: Path,
        recovery_report_path: Path,
        schedule_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            collector = _load(collector_result_path)
        except Exception as exc:
            collector = {}
            issues.append({"code":"INVALID_COLLECTOR_RESULT","blocking":True,"detail":str(exc)})

        if not collector:
            issues.append({"code":"COLLECTOR_RESULT_NOT_FOUND","blocking":True,"detail":str(collector_result_path)})

        status = str(collector.get("status","")).upper()
        state = str(collector.get("state","")).upper()
        safe = bool(collector.get("safe_mode_engaged",False))
        collector_ready = bool(collector.get("automatic_snapshot_collector_ready",False))
        collector_id = str(collector.get("collector_id","")).strip()
        pilot_id = str(collector.get("pilot_id","")).strip()

        if status == "BLOCKED" or safe:
            issues.append({"code":"SOURCE_COLLECTOR_SAFE_MODE","blocking":True,"detail":state})

        required = collector_ready or state == "AUTOMATIC_SNAPSHOT_COLLECTION_READY"

        policy = {}
        recovery = {}
        if required:
            for name,path in (("SCHEDULE_POLICY",schedule_policy_path),("RECOVERY_SNAPSHOT",recovery_snapshot_path)):
                try:
                    loaded = _load(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({"code":f"INVALID_{name}","blocking":True,"detail":str(exc)})
                if not loaded:
                    issues.append({"code":f"{name}_NOT_FOUND","blocking":True,"detail":str(path)})
                if name=="SCHEDULE_POLICY":
                    policy=loaded
                else:
                    recovery=loaded

        policy_ready=False
        schedule_id=""
        if policy:
            schedule_id=str(policy.get("schedule_id","")).strip()
            checks=[
                ("SCHEDULE_ID_MISSING",bool(schedule_id)),
                ("TASK_NAME_MISSING",bool(str(policy.get("task_name","")).strip())),
                ("READ_ONLY_REQUIRED",bool(policy.get("read_only",False))),
                ("ORDER_SUBMISSION_MUST_BE_DISABLED",not bool(policy.get("order_submission_enabled",True))),
                ("LIVE_TRADING_MUST_BE_DISABLED",not bool(policy.get("live_trading_enabled",True))),
                ("NETWORK_WRITE_MUST_BE_DISABLED",not bool(policy.get("network_write_enabled",True))),
                ("INVALID_INTERVAL_MINUTES",5 <= int(policy.get("interval_minutes",0)) <= 1440),
                ("UNBOUNDED_RETRY_BLOCKED",1 <= int(policy.get("max_retries",0)) <= 5),
                ("AUTO_INSTALL_MUST_BE_DISABLED",not bool(policy.get("auto_install_task",True))),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"Windows schedule policy gate failed"})
            policy_ready=all(passed for _,passed in checks)

        recovery_ready=False
        recovery_required=False
        if recovery:
            recovery_required=bool(recovery.get("recovery_required",False))
            checks=[
                ("DUPLICATE_TASK_INSTANCE",int(recovery.get("active_task_instances",0)) <= 1),
                ("UNRESOLVED_SNAPSHOT_WRITE",not bool(recovery.get("snapshot_write_in_progress",False))),
                ("CORRUPTED_CURRENT_SNAPSHOT",not bool(recovery.get("current_snapshot_corrupted",False))),
                ("CREDENTIALS_NOT_AVAILABLE",bool(recovery.get("credentials_available",False))),
                ("RECOVERY_NOT_VERIFIED",bool(recovery.get("recovery_verified",False))),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"scheduled recovery gate failed"})
            recovery_ready=all(passed for _,passed in checks)

        blocking=sum(1 for i in issues if i.get("blocking"))
        plan_ready=bool(required and policy_ready and recovery_ready and blocking==0)

        now=datetime.now(timezone.utc).isoformat()
        task_plan_written=heartbeat_written=recovery_written=token_written=False
        duplicate_token=False

        if plan_ready:
            task_plan={
                "stage":"OP1.17",
                "schedule_id":schedule_id,
                "task_name":str(policy["task_name"]),
                "interval_minutes":int(policy["interval_minutes"]),
                "max_retries":int(policy["max_retries"]),
                "command":"powershell.exe -ExecutionPolicy Bypass -File RUN_OP1_13_TO_OP1_16_SNAPSHOT_COLLECTOR.ps1 -EnableNetwork",
                "task_installation_requested":False,
                "task_installed":False,
                "read_only":True,
                "order_submission_enabled":False,
                "live_trading_enabled":False,
                "created_at":now,
            }
            _write(task_plan_path,task_plan)
            task_plan_written=True

            _write(heartbeat_path,{
                "stage":"OP1.18",
                "schedule_id":schedule_id,
                "collector_id":collector_id,
                "status":"SCHEDULE_PLAN_READY",
                "heartbeat_at":now,
                "expected_interval_minutes":int(policy["interval_minutes"]),
            })
            heartbeat_written=True

            _write(recovery_report_path,{
                "stage":"OP1.19",
                "schedule_id":schedule_id,
                "recovery_required":recovery_required,
                "recovery_ready":recovery_ready,
                "recovery_action":"RETRY_READ_ONLY_COLLECTION" if recovery_required else "NO_RECOVERY_NEEDED",
                "max_retries":int(policy["max_retries"]),
                "created_at":now,
            })
            recovery_written=True

            token={
                "stage_range":"OP1.17-OP1.20",
                "pilot_id":pilot_id,
                "collector_id":collector_id,
                "schedule_id":schedule_id,
                "windows_scheduled_collection_ready":True,
                "task_installed":False,
                "automatic_start_enabled":False,
                "read_only":True,
                "order_submission_enabled":False,
                "network_write_enabled":False,
                "live_trading_enabled":False,
                "created_at":now,
            }
            if schedule_token_path.exists():
                existing=_load(schedule_token_path)
                if existing.get("schedule_id")==schedule_id:
                    duplicate_token=True
                else:
                    issues.append({"code":"SCHEDULE_TOKEN_CONFLICT","blocking":True,"detail":"another schedule token exists"})
            else:
                _write(schedule_token_path,token)
                token_written=True

        blocking=sum(1 for i in issues if i.get("blocking"))
        safe_mode=blocking>0
        final_ready=bool(
            plan_ready and task_plan_written and heartbeat_written and recovery_written
            and (token_written or duplicate_token) and not safe_mode
        )

        if safe_mode:
            out_state,out_status="WINDOWS_SCHEDULED_COLLECTION_SAFE_MODE","BLOCKED"
        elif final_ready:
            out_state,out_status="WINDOWS_SCHEDULED_READ_ONLY_PLAN_READY","PASS"
        else:
            out_state,out_status="WAIT_AUTOMATIC_SNAPSHOT_COLLECTOR","PASS"

        result={
            "stage_range":"OP1.17-OP1.20",
            "implementation_type":"WINDOWS_SCHEDULED_READ_ONLY_COLLECTION",
            "status":out_status,
            "state":out_state,
            "pilot_id":pilot_id,
            "collector_id":collector_id,
            "schedule_id":schedule_id,
            "policy_ready":policy_ready,
            "recovery_ready":recovery_ready,
            "recovery_required":recovery_required,
            "task_plan_written":task_plan_written,
            "heartbeat_written":heartbeat_written,
            "recovery_report_written":recovery_written,
            "schedule_token_written":token_written,
            "duplicate_schedule_token":duplicate_token,
            "windows_scheduled_collection_ready":final_ready,
            "task_installed":False,
            "automatic_start_enabled":False,
            "read_only":True,
            "order_submission_enabled":False,
            "network_write_enabled":False,
            "live_trading_enabled":False,
            "actual_credentials_used":False,
            "actual_external_network_used":False,
            "network_requests_executed":0,
            "write_requests_executed":0,
            "actual_paper_orders_submitted":0,
            "live_orders_submitted":0,
            "safe_mode_engaged":safe_mode,
            "issue_count":len(issues),
            "blocking_issue_count":blocking,
            "issues":issues,
            "next_phase":"OP2_01_SHADOW_DECISION_BOOTSTRAP" if final_ready else "OP1_17_TO_OP1_20_WAIT_COLLECTOR",
            "validation_mode":"LOCAL_WINDOWS_SCHEDULE_PLAN_ONLY",
            "observed_at":now,
            "result_path":str(result_path.resolve()),
        }
        _write(result_path,result)
        return result
