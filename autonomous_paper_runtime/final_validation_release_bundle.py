from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FAILURE_SCENARIOS = {
    "NETWORK_DISCONNECT",
    "API_TIMEOUT",
    "PROCESS_CRASH",
    "DUPLICATE_RUNNER",
    "CORRUPTED_SNAPSHOT",
    "MARKET_CLOSED",
    "BROKER_DELAY",
    "INVALID_TOKEN",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _sha256(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class FinalValidationReleaseBundle:
    def run(
        self,
        *,
        stability_result_path: Path,
        stability_token_path: Path,
        multi_day_snapshot_path: Path,
        failure_injection_snapshot_path: Path,
        deployment_readiness_snapshot_path: Path,
        validation_certificate_path: Path,
        failure_certificate_path: Path,
        release_manifest_path: Path,
        production_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            stability = _load_json(stability_result_path)
        except Exception as exc:
            stability = {}
            issues.append({
                "code": "INVALID_STABILITY_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not stability:
            issues.append({
                "code": "STABILITY_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(stability_result_path),
            })

        source_status = str(stability.get("status", "")).upper()
        source_state = str(stability.get("state", "")).upper()
        source_safe = bool(stability.get("safe_mode_engaged", False))
        stability_ready = bool(stability.get("operational_stability_ready", False))
        engine_id = str(stability.get("engine_id", "")).strip()

        if source_status == "BLOCKED" or source_safe:
            issues.append({
                "code": "SOURCE_STABILITY_SAFE_MODE",
                "blocking": True,
                "detail": source_state,
            })

        required = stability_ready or source_state == "PAPER_RUNTIME_STABILITY_READY"
        stability_token: dict[str, Any] = {}
        multi_day: dict[str, Any] = {}
        failure: dict[str, Any] = {}
        deployment: dict[str, Any] = {}

        if required:
            for code, path in (
                ("STABILITY_TOKEN", stability_token_path),
                ("MULTI_DAY_SNAPSHOT", multi_day_snapshot_path),
                ("FAILURE_INJECTION_SNAPSHOT", failure_injection_snapshot_path),
                ("DEPLOYMENT_READINESS_SNAPSHOT", deployment_readiness_snapshot_path),
            ):
                try:
                    loaded = _load_json(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({
                        "code": f"INVALID_{code}",
                        "blocking": True,
                        "detail": str(exc),
                    })

                if not loaded:
                    issues.append({
                        "code": f"{code}_NOT_FOUND",
                        "blocking": True,
                        "detail": str(path),
                    })

                if code == "STABILITY_TOKEN":
                    stability_token = loaded
                elif code == "MULTI_DAY_SNAPSHOT":
                    multi_day = loaded
                elif code == "FAILURE_INJECTION_SNAPSHOT":
                    failure = loaded
                else:
                    deployment = loaded

        if stability_token and (
            stability_token.get("engine_id") != engine_id
            or not bool(stability_token.get("operational_stability_ready", False))
        ):
            issues.append({
                "code": "STABILITY_TOKEN_MISMATCH",
                "blocking": True,
                "detail": "stability result and token do not match",
            })

        multi_day_ready = False
        if multi_day:
            completed_days = int(multi_day.get("completed_trading_days", 0))
            minimum_days = int(multi_day.get("minimum_trading_days", 20))
            checks = [
                ("INSUFFICIENT_TRADING_DAYS", completed_days >= minimum_days),
                ("DUPLICATE_ORDERS_DETECTED", int(multi_day.get("duplicate_orders", 0)) == 0),
                ("LIVE_ORDERS_DETECTED", int(multi_day.get("live_orders", 0)) == 0),
                ("RISK_VIOLATIONS_DETECTED", int(multi_day.get("risk_violations", 0)) == 0),
                ("RECOVERY_FAILURES_DETECTED", int(multi_day.get("recovery_failures", 0)) == 0),
                ("LEDGER_MISMATCHES_DETECTED", int(multi_day.get("ledger_mismatches", 0)) == 0),
                ("RECONCILIATION_ERRORS_DETECTED", int(multi_day.get("reconciliation_errors", 0)) == 0),
                ("UNEXPECTED_WRITES_DETECTED", int(multi_day.get("unexpected_broker_writes", 0)) == 0),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "multi-day stability criterion failed",
                    })
            multi_day_ready = all(passed for _, passed in checks)

        failure_injection_ready = False
        scenario_results: list[dict[str, Any]] = []
        if failure:
            scenario_results = list(failure.get("scenarios", []))
            observed_names = {
                str(item.get("name", "")).upper()
                for item in scenario_results
                if isinstance(item, dict)
            }
            missing_scenarios = sorted(REQUIRED_FAILURE_SCENARIOS - observed_names)
            if missing_scenarios:
                issues.append({
                    "code": "FAILURE_SCENARIOS_MISSING",
                    "blocking": True,
                    "detail": ",".join(missing_scenarios),
                })

            failed_scenarios = []
            for item in scenario_results:
                if not isinstance(item, dict):
                    failed_scenarios.append("<invalid>")
                    continue
                passed = (
                    bool(item.get("safe_mode_or_recovery_passed", False))
                    and int(item.get("duplicate_orders", 0)) == 0
                    and int(item.get("live_orders", 0)) == 0
                    and int(item.get("unexpected_writes", 0)) == 0
                )
                if not passed:
                    failed_scenarios.append(str(item.get("name", "<unknown>")))

            if failed_scenarios:
                issues.append({
                    "code": "FAILURE_INJECTION_FAILED",
                    "blocking": True,
                    "detail": ",".join(failed_scenarios),
                })

            failure_injection_ready = (
                not missing_scenarios
                and not failed_scenarios
                and len(scenario_results) >= len(REQUIRED_FAILURE_SCENARIOS)
            )

        deployment_ready = False
        if deployment:
            checks = [
                ("INSTALL_SCRIPT_MISSING", bool(deployment.get("install_script_ready", False))),
                ("ROLLBACK_MISSING", bool(deployment.get("rollback_ready", False))),
                ("EMERGENCY_STOP_MISSING", bool(deployment.get("emergency_stop_ready", False))),
                ("RECOVERY_RUNBOOK_MISSING", bool(deployment.get("recovery_runbook_ready", False))),
                ("SCHEDULER_SETUP_MISSING", bool(deployment.get("scheduler_setup_ready", False))),
                ("DAILY_REPORT_MISSING", bool(deployment.get("daily_report_ready", False))),
                ("SECRET_STORAGE_UNSAFE", bool(deployment.get("secret_storage_safe", False))),
                ("LIVE_ENDPOINT_NOT_BLOCKED", bool(deployment.get("live_endpoint_blocked", False))),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "production readiness criterion failed",
                    })
            deployment_ready = all(passed for _, passed in checks)

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0

        validation_written = False
        failure_written = False
        manifest_written = False
        token_written = False
        duplicate_token = False
        release_id = ""

        final_ready = bool(
            required
            and stability_token
            and multi_day_ready
            and failure_injection_ready
            and deployment_ready
            and not safe_mode
        )

        if final_ready:
            validation_core = {
                "stage": "V141.06",
                "engine_id": engine_id,
                "completed_trading_days": int(
                    multi_day.get("completed_trading_days", 0)
                ),
                "minimum_trading_days": int(
                    multi_day.get("minimum_trading_days", 20)
                ),
                "multi_day_validation_passed": True,
                "duplicate_orders": 0,
                "live_orders": 0,
                "risk_violations": 0,
                "recovery_failures": 0,
                "ledger_mismatches": 0,
                "reconciliation_errors": 0,
                "unexpected_broker_writes": 0,
            }
            validation_payload = {
                **validation_core,
                "certificate_hash": _sha256(validation_core),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _write_json(validation_certificate_path, validation_payload)
            validation_written = True

            failure_core = {
                "stage": "V141.07",
                "engine_id": engine_id,
                "required_scenario_count": len(REQUIRED_FAILURE_SCENARIOS),
                "passed_scenario_count": len(scenario_results),
                "failure_injection_passed": True,
                "scenario_names": sorted(REQUIRED_FAILURE_SCENARIOS),
            }
            failure_payload = {
                **failure_core,
                "certificate_hash": _sha256(failure_core),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _write_json(failure_certificate_path, failure_payload)
            failure_written = True

            release_id = "paper-release-" + hashlib.sha256(
                (
                    validation_payload["certificate_hash"]
                    + "|"
                    + failure_payload["certificate_hash"]
                    + "|"
                    + engine_id
                ).encode("utf-8")
            ).hexdigest()[:24]

            manifest_payload = {
                "stage": "V141.08",
                "release_id": release_id,
                "engine_id": engine_id,
                "paper_production_release_ready": True,
                "install_script_ready": True,
                "rollback_ready": True,
                "emergency_stop_ready": True,
                "recovery_runbook_ready": True,
                "scheduler_setup_ready": True,
                "daily_report_ready": True,
                "secret_storage_safe": True,
                "live_endpoint_blocked": True,
                "validation_certificate_path": str(
                    validation_certificate_path.resolve()
                ),
                "failure_certificate_path": str(
                    failure_certificate_path.resolve()
                ),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _write_json(release_manifest_path, manifest_payload)
            manifest_written = True

            token_payload = {
                "stage": "V141.08",
                "release_id": release_id,
                "engine_id": engine_id,
                "paper_production_release_ready": True,
                "live_trading_enabled": False,
                "actual_submission_allowed": False,
                "broker_network_allowed": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            if production_token_path.exists():
                existing = _load_json(production_token_path)
                if existing.get("release_id") == release_id:
                    duplicate_token = True
                else:
                    issues.append({
                        "code": "PRODUCTION_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "existing token belongs to another release",
                    })
            else:
                _write_json(production_token_path, token_payload)
                token_written = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        production_release_ready = bool(
            final_ready
            and validation_written
            and failure_written
            and manifest_written
            and (token_written or duplicate_token)
            and not safe_mode
        )

        if safe_mode:
            state, status = "FINAL_VALIDATION_SAFE_MODE", "BLOCKED"
        elif production_release_ready:
            state, status = "PAPER_PRODUCTION_RELEASE_READY", "PASS"
        else:
            state, status = "WAIT_OPERATIONAL_STABILITY", "PASS"

        result = {
            "stage_range": "V141.06-V141.08",
            "implementation_type": "ULTRA_FAST_FINAL_VALIDATION_RELEASE",
            "status": status,
            "state": state,
            "engine_id": engine_id,
            "release_id": release_id,
            "multi_day_validation_ready": multi_day_ready,
            "failure_injection_ready": failure_injection_ready,
            "deployment_readiness_ready": deployment_ready,
            "validation_certificate_written": validation_written,
            "failure_certificate_written": failure_written,
            "release_manifest_written": manifest_written,
            "production_token_written": token_written,
            "duplicate_production_token": duplicate_token,
            "paper_production_release_ready": production_release_ready,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "V142_01_AUTONOMOUS_PAPER_RUNTIME"
                if production_release_ready
                else "V141_06_TO_V141_08_WAIT_OPERATIONAL_STABILITY"
            ),
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "live_trading_enabled": False,
            "validation_mode": "LOCAL_FINAL_VALIDATION_ONLY",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "result_path": str(result_path.resolve()),
        }
        _write_json(result_path, result)
        return result
