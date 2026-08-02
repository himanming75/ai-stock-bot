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
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


class ShadowDailyAutomation:
    def run(
        self,
        *,
        pipeline_result_path: Path,
        runtime_policy_path: Path,
        recovery_snapshot_path: Path,
        daily_evidence_path: Path,
        scheduler_state_path: Path,
        heartbeat_path: Path,
        recovery_report_path: Path,
        daily_report_path: Path,
        automation_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            source = _load(pipeline_result_path)
        except Exception as exc:
            source = {}
            issues.append({
                "code": "INVALID_PIPELINE_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not source:
            issues.append({
                "code": "PIPELINE_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(pipeline_result_path),
            })

        source_status = str(source.get("status", "")).upper()
        source_state = str(source.get("state", "")).upper()
        source_safe = bool(source.get("safe_mode_engaged", False))
        source_ready = bool(
            source.get("automatic_shadow_signal_pipeline_ready", False)
        )
        pipeline_id = str(source.get("pipeline_id", "")).strip()
        shadow_session_id = str(
            source.get("shadow_session_id", "")
        ).strip()

        if source_status == "BLOCKED" or source_safe:
            issues.append({
                "code": "SOURCE_PIPELINE_SAFE_MODE",
                "blocking": True,
                "detail": source_state,
            })

        required = (
            source_ready
            or source_state == "AUTOMATIC_SHADOW_SIGNAL_PIPELINE_READY"
        )

        policy: dict[str, Any] = {}
        recovery: dict[str, Any] = {}
        evidence: dict[str, Any] = {}

        if required:
            for name, path in (
                ("RUNTIME_POLICY", runtime_policy_path),
                ("RECOVERY_SNAPSHOT", recovery_snapshot_path),
                ("DAILY_EVIDENCE", daily_evidence_path),
            ):
                try:
                    loaded = _load(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({
                        "code": f"INVALID_{name}",
                        "blocking": True,
                        "detail": str(exc),
                    })

                if not loaded:
                    issues.append({
                        "code": f"{name}_NOT_FOUND",
                        "blocking": True,
                        "detail": str(path),
                    })

                if name == "RUNTIME_POLICY":
                    policy = loaded
                elif name == "RECOVERY_SNAPSHOT":
                    recovery = loaded
                else:
                    evidence = loaded

        runtime_id = ""
        policy_ready = False
        if policy:
            runtime_id = str(policy.get("runtime_id", "")).strip()
            checks = [
                ("RUNTIME_ID_MISSING", bool(runtime_id)),
                (
                    "SHADOW_ONLY_REQUIRED",
                    bool(policy.get("shadow_only", False)),
                ),
                (
                    "ORDER_SUBMISSION_MUST_BE_DISABLED",
                    not bool(policy.get("order_submission_enabled", True)),
                ),
                (
                    "BROKER_WRITE_MUST_BE_DISABLED",
                    not bool(policy.get("broker_write_enabled", True)),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
                (
                    "CONTINUOUS_LOOP_MUST_BE_DISABLED",
                    not bool(policy.get("continuous_loop_enabled", True)),
                ),
                (
                    "INVALID_MAX_RETRIES",
                    1 <= int(policy.get("max_retries", 0)) <= 5,
                ),
                (
                    "INVALID_HEARTBEAT_MINUTES",
                    1 <= int(policy.get("heartbeat_interval_minutes", 0)) <= 60,
                ),
                (
                    "AUTO_INSTALL_MUST_BE_DISABLED",
                    not bool(policy.get("auto_install_task", True)),
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "daily automation policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        recovery_ready = False
        recovery_required = False
        if recovery:
            recovery_required = bool(
                recovery.get("recovery_required", False)
            )
            checks = [
                (
                    "DUPLICATE_RUNTIME_INSTANCE",
                    int(recovery.get("active_runtime_instances", 0)) <= 1,
                ),
                (
                    "UNRESOLVED_RUNTIME_LOCK",
                    not bool(recovery.get("runtime_lock_held", False)),
                ),
                (
                    "CORRUPTED_QUEUE",
                    not bool(recovery.get("signal_queue_corrupted", False)),
                ),
                (
                    "RECOVERY_NOT_VERIFIED",
                    bool(recovery.get("recovery_verified", False)),
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "daily automation recovery gate failed",
                    })
            recovery_ready = all(passed for _, passed in checks)

        evidence_ready = False
        signal_count = buy_count = sell_count = hold_count = 0
        risk_block_count = error_count = 0
        total_pnl = max_drawdown_pct = 0.0
        runtime_seconds = 0

        if evidence:
            signal_count = int(evidence.get("signal_count", 0))
            buy_count = int(evidence.get("buy_count", 0))
            sell_count = int(evidence.get("sell_count", 0))
            hold_count = int(evidence.get("hold_count", 0))
            risk_block_count = int(evidence.get("risk_block_count", 0))
            error_count = int(evidence.get("error_count", 0))
            total_pnl = float(evidence.get("total_pnl", 0))
            max_drawdown_pct = float(
                evidence.get("max_drawdown_pct", 0)
            )
            runtime_seconds = int(evidence.get("runtime_seconds", 0))

            checks = [
                (
                    "SIGNAL_COUNT_MISMATCH",
                    signal_count == buy_count + sell_count + hold_count,
                ),
                (
                    "NEGATIVE_SIGNAL_COUNT",
                    min(
                        signal_count,
                        buy_count,
                        sell_count,
                        hold_count,
                        risk_block_count,
                        error_count,
                    ) >= 0,
                ),
                (
                    "NEGATIVE_RUNTIME_SECONDS",
                    runtime_seconds >= 0,
                ),
                (
                    "MAX_DRAWDOWN_INVALID",
                    0 <= max_drawdown_pct <= 100,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "daily evidence validation failed",
                    })
            evidence_ready = all(passed for _, passed in checks)

        blocking = sum(1 for item in issues if item.get("blocking"))
        runtime_ready = bool(
            required
            and policy_ready
            and recovery_ready
            and evidence_ready
            and blocking == 0
        )

        now = datetime.now(timezone.utc).isoformat()
        scheduler_written = heartbeat_written = False
        recovery_written = report_written = False
        token_written = duplicate_token = False

        if runtime_ready:
            _write(scheduler_state_path, {
                "stage": "OP2.17",
                "runtime_id": runtime_id,
                "pipeline_id": pipeline_id,
                "shadow_session_id": shadow_session_id,
                "runtime_tick": 1,
                "scheduler_mode": "LOCAL_SINGLE_DAILY_TICK",
                "continuous_loop_enabled": False,
                "automatic_task_installed": False,
                "created_at": now,
            })
            scheduler_written = True

            _write(heartbeat_path, {
                "stage": "OP2.18",
                "runtime_id": runtime_id,
                "heartbeat_status": "HEALTHY",
                "heartbeat_at": now,
                "expected_interval_minutes": int(
                    policy["heartbeat_interval_minutes"]
                ),
            })
            heartbeat_written = True

            _write(recovery_report_path, {
                "stage": "OP2.19",
                "runtime_id": runtime_id,
                "recovery_required": recovery_required,
                "recovery_ready": recovery_ready,
                "recovery_action": (
                    "RESUME_SHADOW_DAILY_TICK"
                    if recovery_required
                    else "NO_RECOVERY_NEEDED"
                ),
                "max_retries": int(policy["max_retries"]),
                "created_at": now,
            })
            recovery_written = True

            _write(daily_report_path, {
                "stage": "OP2.20",
                "runtime_id": runtime_id,
                "shadow_session_id": shadow_session_id,
                "signal_count": signal_count,
                "buy_count": buy_count,
                "sell_count": sell_count,
                "hold_count": hold_count,
                "risk_block_count": risk_block_count,
                "error_count": error_count,
                "total_pnl": total_pnl,
                "max_drawdown_pct": max_drawdown_pct,
                "runtime_seconds": runtime_seconds,
                "shadow_only": True,
                "order_submission_enabled": False,
                "broker_write_enabled": False,
                "live_trading_enabled": False,
                "daily_shadow_report_ready": True,
                "created_at": now,
            })
            report_written = True

            token = {
                "stage_range": "OP2.17-OP2.20",
                "runtime_id": runtime_id,
                "pipeline_id": pipeline_id,
                "shadow_daily_automation_ready": True,
                "single_tick_only": True,
                "continuous_loop_enabled": False,
                "automatic_task_installed": False,
                "shadow_only": True,
                "order_submission_enabled": False,
                "broker_write_enabled": False,
                "live_trading_enabled": False,
                "created_at": now,
            }

            if automation_token_path.exists():
                existing = _load(automation_token_path)
                if existing.get("runtime_id") == runtime_id:
                    duplicate_token = True
                else:
                    issues.append({
                        "code": "AUTOMATION_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "another runtime owns the token",
                    })
            else:
                _write(automation_token_path, token)
                token_written = True

        blocking = sum(1 for item in issues if item.get("blocking"))
        safe_mode = blocking > 0

        final_ready = bool(
            runtime_ready
            and scheduler_written
            and heartbeat_written
            and recovery_written
            and report_written
            and (token_written or duplicate_token)
            and not safe_mode
        )

        if safe_mode:
            state, status = "SHADOW_DAILY_AUTOMATION_SAFE_MODE", "BLOCKED"
        elif final_ready:
            state, status = "SHADOW_DAILY_AUTOMATION_READY", "PASS"
        else:
            state, status = "WAIT_AUTOMATIC_SHADOW_PIPELINE", "PASS"

        result = {
            "stage_range": "OP2.17-OP2.20",
            "implementation_type": "SHADOW_DAILY_AUTOMATION",
            "status": status,
            "state": state,
            "shadow_session_id": shadow_session_id,
            "pipeline_id": pipeline_id,
            "runtime_id": runtime_id,
            "policy_ready": policy_ready,
            "recovery_ready": recovery_ready,
            "recovery_required": recovery_required,
            "evidence_ready": evidence_ready,
            "scheduler_state_written": scheduler_written,
            "heartbeat_written": heartbeat_written,
            "recovery_report_written": recovery_written,
            "daily_shadow_report_written": report_written,
            "automation_token_written": token_written,
            "duplicate_automation_token": duplicate_token,
            "shadow_daily_automation_ready": final_ready,
            "signal_count": signal_count,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "risk_block_count": risk_block_count,
            "error_count": error_count,
            "total_pnl": total_pnl,
            "max_drawdown_pct": max_drawdown_pct,
            "runtime_seconds": runtime_seconds,
            "single_tick_only": True,
            "continuous_loop_enabled": False,
            "automatic_task_installed": False,
            "shadow_only": True,
            "order_submission_enabled": False,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "DASH1_01_DASHBOARD_FOUNDATION"
                if final_ready
                else "OP2_17_TO_OP2_20_WAIT_PIPELINE"
            ),
            "validation_mode": "LOCAL_SINGLE_DAILY_SHADOW_TICK_ONLY",
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
