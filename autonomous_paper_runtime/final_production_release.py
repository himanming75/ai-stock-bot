from __future__ import annotations

import hashlib
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
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def _hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class FinalProductionRelease:
    def run(
        self,
        *,
        scheduled_result_path: Path,
        scheduled_token_path: Path,
        deployment_snapshot_path: Path,
        rollback_snapshot_path: Path,
        installer_snapshot_path: Path,
        production_certificate_path: Path,
        deployment_manifest_path: Path,
        rollback_manifest_path: Path,
        final_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            scheduled = _load(scheduled_result_path)
        except Exception as exc:
            scheduled = {}
            issues.append({"code":"INVALID_SCHEDULED_RESULT","blocking":True,"detail":str(exc)})

        if not scheduled:
            issues.append({"code":"SCHEDULED_RESULT_NOT_FOUND","blocking":True,"detail":str(scheduled_result_path)})

        source_status = str(scheduled.get("status","")).upper()
        source_state = str(scheduled.get("state","")).upper()
        source_safe = bool(scheduled.get("safe_mode_engaged",False))
        scheduled_ready = bool(scheduled.get("scheduled_runtime_ready",False))
        scheduled_runtime_id = str(scheduled.get("scheduled_runtime_id","")).strip()
        runtime_id = str(scheduled.get("runtime_id","")).strip()

        if source_status == "BLOCKED" or source_safe:
            issues.append({"code":"SOURCE_SCHEDULED_RUNTIME_SAFE_MODE","blocking":True,"detail":source_state})

        required = scheduled_ready or source_state == "AUTONOMOUS_RUNTIME_SCHEDULE_READY"
        token = deployment = rollback = installer = {}

        if required:
            for name,path in (
                ("SCHEDULED_TOKEN",scheduled_token_path),
                ("DEPLOYMENT_SNAPSHOT",deployment_snapshot_path),
                ("ROLLBACK_SNAPSHOT",rollback_snapshot_path),
                ("INSTALLER_SNAPSHOT",installer_snapshot_path),
            ):
                try:
                    loaded = _load(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({"code":f"INVALID_{name}","blocking":True,"detail":str(exc)})
                if not loaded:
                    issues.append({"code":f"{name}_NOT_FOUND","blocking":True,"detail":str(path)})
                if name=="SCHEDULED_TOKEN": token=loaded
                elif name=="DEPLOYMENT_SNAPSHOT": deployment=loaded
                elif name=="ROLLBACK_SNAPSHOT": rollback=loaded
                else: installer=loaded

        if token and (
            token.get("scheduled_runtime_id") != scheduled_runtime_id
            or not bool(token.get("scheduled_runtime_ready",False))
            or bool(token.get("continuous_loop_enabled",True))
            or bool(token.get("actual_submission_allowed",True))
            or bool(token.get("broker_network_allowed",True))
            or bool(token.get("live_trading_enabled",True))
        ):
            issues.append({"code":"SCHEDULED_TOKEN_MISMATCH","blocking":True,"detail":"scheduled token violates final release contract"})

        deployment_ready = False
        if deployment:
            checks = [
                ("WINDOWS_TASK_NOT_REVIEWED",bool(deployment.get("windows_task_reviewed",False))),
                ("SERVICE_ACCOUNT_NOT_REVIEWED",bool(deployment.get("service_account_reviewed",False))),
                ("LOG_ROTATION_NOT_READY",bool(deployment.get("log_rotation_ready",False))),
                ("MONITORING_NOT_READY",bool(deployment.get("monitoring_ready",False))),
                ("SECRET_STORAGE_UNSAFE",bool(deployment.get("secret_storage_safe",False))),
                ("PAPER_ENDPOINT_UNVERIFIED",bool(deployment.get("paper_endpoint_verified",False))),
                ("LIVE_ENDPOINT_NOT_BLOCKED",bool(deployment.get("live_endpoint_blocked",False))),
                ("EMERGENCY_STOP_NOT_READY",bool(deployment.get("emergency_stop_ready",False))),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"deployment readiness gate failed"})
            deployment_ready = all(passed for _,passed in checks)

        rollback_ready = False
        if rollback:
            checks = [
                ("ROLLBACK_SCRIPT_MISSING",bool(rollback.get("rollback_script_ready",False))),
                ("BACKUP_MISSING",bool(rollback.get("configuration_backup_ready",False))),
                ("TOKEN_REVOCATION_MISSING",bool(rollback.get("token_revocation_ready",False))),
                ("TASK_DISABLE_MISSING",bool(rollback.get("scheduled_task_disable_ready",False))),
                ("RECOVERY_VERIFICATION_MISSING",bool(rollback.get("post_rollback_verification_ready",False))),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"rollback readiness gate failed"})
            rollback_ready = all(passed for _,passed in checks)

        installer_ready = False
        if installer:
            checks = [
                ("INSTALLER_SCRIPT_MISSING",bool(installer.get("installer_script_ready",False))),
                ("INSTALL_CHECK_MISSING",bool(installer.get("install_check_ready",False))),
                ("VERIFY_SCRIPT_MISSING",bool(installer.get("verify_script_ready",False))),
                ("RUNBOOK_MISSING",bool(installer.get("runbook_ready",False))),
                ("CHECKSUM_MISSING",bool(installer.get("checksum_ready",False))),
                ("UNINSTALLER_MISSING",bool(installer.get("uninstaller_ready",False))),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"installer readiness gate failed"})
            installer_ready = all(passed for _,passed in checks)

        blocking = sum(1 for x in issues if x.get("blocking"))
        ready = bool(required and token and deployment_ready and rollback_ready and installer_ready and not blocking)

        cert_written = deploy_written = rollback_written = token_written = False
        duplicate_token = False
        release_id = ""

        if ready:
            core = {
                "stage":"V143.FINAL",
                "scheduled_runtime_id":scheduled_runtime_id,
                "runtime_id":runtime_id,
                "paper_runtime_release_ready":True,
                "live_trading_enabled":False,
                "actual_submission_allowed":False,
                "broker_network_allowed":False,
                "deployment_ready":True,
                "rollback_ready":True,
                "installer_ready":True,
            }
            certificate_hash = _hash(core)
            release_id = "v143-paper-final-" + certificate_hash[:24]
            _write(production_certificate_path,{
                **core,
                "release_id":release_id,
                "certificate_hash":certificate_hash,
                "created_at":datetime.now(timezone.utc).isoformat(),
            })
            cert_written = True

            _write(deployment_manifest_path,{
                "release_id":release_id,
                "deployment_mode":"PAPER_ONLY_DISABLED_BY_DEFAULT",
                "scheduled_runtime_id":scheduled_runtime_id,
                "windows_task_reviewed":True,
                "monitoring_ready":True,
                "secret_storage_safe":True,
                "paper_endpoint_verified":True,
                "live_endpoint_blocked":True,
                "automatic_start_enabled":False,
                "created_at":datetime.now(timezone.utc).isoformat(),
            })
            deploy_written = True

            _write(rollback_manifest_path,{
                "release_id":release_id,
                "rollback_script_ready":True,
                "configuration_backup_ready":True,
                "token_revocation_ready":True,
                "scheduled_task_disable_ready":True,
                "post_rollback_verification_ready":True,
                "created_at":datetime.now(timezone.utc).isoformat(),
            })
            rollback_written = True

            final_token = {
                "stage":"V143.FINAL",
                "release_id":release_id,
                "scheduled_runtime_id":scheduled_runtime_id,
                "final_production_package_ready":True,
                "paper_runtime_ready_for_manual_deployment":True,
                "automatic_start_enabled":False,
                "continuous_loop_enabled":False,
                "actual_submission_allowed":False,
                "broker_network_allowed":False,
                "live_trading_enabled":False,
                "created_at":datetime.now(timezone.utc).isoformat(),
            }
            if final_token_path.exists():
                existing=_load(final_token_path)
                if existing.get("release_id")==release_id:
                    duplicate_token=True
                else:
                    issues.append({"code":"FINAL_TOKEN_CONFLICT","blocking":True,"detail":"another release token exists"})
            else:
                _write(final_token_path,final_token)
                token_written=True

        blocking=sum(1 for x in issues if x.get("blocking"))
        safe_mode=blocking>0
        final_ready=bool(ready and cert_written and deploy_written and rollback_written and (token_written or duplicate_token) and not safe_mode)

        if safe_mode:
            out_state,out_status="FINAL_PRODUCTION_SAFE_MODE","BLOCKED"
        elif final_ready:
            out_state,out_status="V143_FINAL_PRODUCTION_PACKAGE_READY","PASS"
        else:
            out_state,out_status="WAIT_SCHEDULED_RUNTIME","PASS"

        result={
            "stage":"V143.FINAL",
            "implementation_type":"FINAL_PRODUCTION_RELEASE_PACKAGE",
            "status":out_status,
            "state":out_state,
            "release_id":release_id,
            "scheduled_runtime_id":scheduled_runtime_id,
            "deployment_ready":deployment_ready,
            "rollback_ready":rollback_ready,
            "installer_ready":installer_ready,
            "production_certificate_written":cert_written,
            "deployment_manifest_written":deploy_written,
            "rollback_manifest_written":rollback_written,
            "final_token_written":token_written,
            "duplicate_final_token":duplicate_token,
            "final_production_package_ready":final_ready,
            "automatic_start_enabled":False,
            "continuous_loop_enabled":False,
            "actual_submission_allowed":False,
            "broker_network_allowed":False,
            "live_trading_enabled":False,
            "safe_mode_engaged":safe_mode,
            "issue_count":len(issues),
            "blocking_issue_count":blocking,
            "issues":issues,
            "next_phase":"PROJECT_COMPLETE_PAPER_RUNTIME_MANUAL_DEPLOYMENT" if final_ready else "V143_WAIT_SCHEDULED_RUNTIME",
            "actual_credentials_used":False,
            "actual_external_network_used":False,
            "network_requests_executed":0,
            "write_requests_executed":0,
            "actual_paper_orders_submitted":0,
            "live_orders_submitted":0,
            "validation_mode":"LOCAL_FINAL_PRODUCTION_PACKAGE_ONLY",
            "observed_at":datetime.now(timezone.utc).isoformat(),
            "result_path":str(result_path.resolve()),
        }
        _write(result_path,result)
        return result
