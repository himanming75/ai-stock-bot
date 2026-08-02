from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _hash_record(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class OperationalStabilityBundle:
    def run(
        self,
        *,
        integration_result_path: Path,
        health_snapshot_path: Path,
        retry_policy_path: Path,
        daily_audit_path: Path,
        process_lock_path: Path,
        integrity_ledger_path: Path,
        health_result_path: Path,
        stability_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            integration = _load_json(integration_result_path)
        except Exception as exc:
            integration = {}
            issues.append({
                "code": "INVALID_INTEGRATION_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not integration:
            issues.append({
                "code": "INTEGRATION_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(integration_result_path),
            })

        source_status = str(integration.get("status", "")).upper()
        source_state = str(integration.get("state", "")).upper()
        source_safe = bool(integration.get("safe_mode_engaged", False))
        integration_ready = bool(integration.get("paper_integration_ready", False))
        engine_id = str(integration.get("engine_id", "")).strip()
        client_order_id = str(integration.get("client_order_id", "")).strip()

        if source_status == "BLOCKED" or source_safe:
            issues.append({
                "code": "SOURCE_INTEGRATION_SAFE_MODE",
                "blocking": True,
                "detail": source_state,
            })

        required = integration_ready or source_state in {
            "PAPER_INTEGRATION_READY_SUBMISSION_DISABLED",
            "ACTUAL_PAPER_AUTONOMOUS_READY",
        }

        health: dict[str, Any] = {}
        retry: dict[str, Any] = {}

        if required:
            for code, path in (
                ("HEALTH_SNAPSHOT", health_snapshot_path),
                ("RETRY_POLICY", retry_policy_path),
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
                if code == "HEALTH_SNAPSHOT":
                    health = loaded
                else:
                    retry = loaded

        lock_acquired = False
        if required and not issues:
            if process_lock_path.exists():
                try:
                    existing_lock = _load_json(process_lock_path)
                except Exception as exc:
                    existing_lock = {}
                    issues.append({
                        "code": "INVALID_PROCESS_LOCK",
                        "blocking": True,
                        "detail": str(exc),
                    })
                if existing_lock and not bool(existing_lock.get("released", False)):
                    issues.append({
                        "code": "PROCESS_LOCK_ACTIVE",
                        "blocking": True,
                        "detail": "another stability process is active",
                    })

            if not any(issue.get("blocking") for issue in issues):
                _write_json(process_lock_path, {
                    "stage_range": "V141.01-V141.05",
                    "released": False,
                    "engine_id": engine_id,
                    "acquired_at": datetime.now(timezone.utc).isoformat(),
                })
                lock_acquired = True

        health_ready = False
        retry_ready = False
        audit_written = False
        integrity_verified = False
        token_written = False
        duplicate_token = False

        try:
            if health:
                checks = [
                    (
                        "DISK_SPACE_LOW",
                        float(health.get("disk_free_mb", 0))
                        >= float(health.get("minimum_disk_free_mb", 1024)),
                    ),
                    (
                        "HEARTBEAT_STALE",
                        int(health.get("heartbeat_age_seconds", 999999))
                        <= int(health.get("maximum_heartbeat_age_seconds", 300)),
                    ),
                    (
                        "FILESYSTEM_NOT_WRITABLE",
                        bool(health.get("filesystem_writable", False)),
                    ),
                    (
                        "CLOCK_NOT_SYNCHRONIZED",
                        bool(health.get("system_clock_synchronized", False)),
                    ),
                    (
                        "DUPLICATE_RUNTIME_PROCESS",
                        int(health.get("runtime_process_count", 0)) <= 1,
                    ),
                    (
                        "LOG_DIRECTORY_UNAVAILABLE",
                        bool(health.get("log_directory_writable", False)),
                    ),
                ]
                for code, passed in checks:
                    if not passed:
                        issues.append({
                            "code": code,
                            "blocking": True,
                            "detail": "operational health gate failed",
                        })
                health_ready = all(passed for _, passed in checks)

            if retry:
                checks = [
                    (
                        "INVALID_MAX_ATTEMPTS",
                        1 <= int(retry.get("max_attempts", 0)) <= 10,
                    ),
                    (
                        "INVALID_INITIAL_BACKOFF",
                        float(retry.get("initial_backoff_seconds", 0)) > 0,
                    ),
                    (
                        "INVALID_MAX_BACKOFF",
                        float(retry.get("maximum_backoff_seconds", 0))
                        >= float(retry.get("initial_backoff_seconds", 0)),
                    ),
                    (
                        "RATE_LIMIT_POLICY_DISABLED",
                        bool(retry.get("rate_limit_enabled", False)),
                    ),
                    (
                        "NON_IDEMPOTENT_WRITE_RETRY",
                        not bool(retry.get("retry_write_without_lookup", True)),
                    ),
                ]
                for code, passed in checks:
                    if not passed:
                        issues.append({
                            "code": code,
                            "blocking": True,
                            "detail": "retry/rate-limit policy gate failed",
                        })
                retry_ready = all(passed for _, passed in checks)

            blocking = sum(1 for issue in issues if issue.get("blocking"))
            if required and health_ready and retry_ready and blocking == 0:
                audit_core = {
                    "stage": "V141.01",
                    "engine_id": engine_id,
                    "client_order_id": client_order_id,
                    "integration_state": source_state,
                    "paper_integration_ready": integration_ready,
                    "actual_external_network_used": bool(
                        integration.get("actual_external_network_used", False)
                    ),
                    "actual_paper_orders_submitted": int(
                        integration.get("actual_paper_orders_submitted", 0)
                    ),
                    "live_orders_submitted": int(
                        integration.get("live_orders_submitted", 0)
                    ),
                    "safe_mode_engaged": source_safe,
                }
                audit_payload = {
                    **audit_core,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                }
                _write_json(daily_audit_path, audit_payload)
                audit_written = True

                previous_hash = ""
                existing_records: list[str] = []
                if integrity_ledger_path.exists():
                    existing_records = [
                        line
                        for line in integrity_ledger_path.read_text(
                            encoding="utf-8"
                        ).splitlines()
                        if line.strip()
                    ]
                    if existing_records:
                        previous = json.loads(existing_records[-1])
                        previous_hash = str(previous.get("record_hash", ""))

                record = {
                    "stage": "V141.04",
                    "engine_id": engine_id,
                    "client_order_id": client_order_id,
                    "previous_hash": previous_hash,
                    "audit_hash": _hash_record(audit_core),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                record["record_hash"] = _hash_record(record)

                duplicate_record = False
                for line in existing_records:
                    item = json.loads(line)
                    if (
                        item.get("engine_id") == engine_id
                        and item.get("audit_hash") == record["audit_hash"]
                    ):
                        duplicate_record = True
                        break

                if not duplicate_record:
                    _append_jsonl(integrity_ledger_path, record)

                records = [
                    json.loads(line)
                    for line in integrity_ledger_path.read_text(
                        encoding="utf-8"
                    ).splitlines()
                    if line.strip()
                ]
                expected_previous = ""
                integrity_verified = True
                for item in records:
                    current = dict(item)
                    stored_hash = current.pop("record_hash", "")
                    if current.get("previous_hash", "") != expected_previous:
                        integrity_verified = False
                        break
                    calculated = _hash_record(current)
                    if calculated != stored_hash:
                        integrity_verified = False
                        break
                    expected_previous = stored_hash

                if not integrity_verified:
                    issues.append({
                        "code": "LEDGER_HASH_CHAIN_INVALID",
                        "blocking": True,
                        "detail": "integrity ledger verification failed",
                    })

                _write_json(health_result_path, {
                    "stage": "V141.05",
                    "engine_id": engine_id,
                    "health_ready": health_ready,
                    "retry_policy_ready": retry_ready,
                    "integrity_verified": integrity_verified,
                    "lock_acquired": lock_acquired,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                })

                blocking = sum(1 for issue in issues if issue.get("blocking"))
                if blocking == 0 and integrity_verified:
                    stability_id = hashlib.sha256(
                        f"{engine_id}|{client_order_id}|{record['audit_hash']}".encode(
                            "utf-8"
                        )
                    ).hexdigest()[:24]
                    token = {
                        "stage_range": "V141.01-V141.05",
                        "stability_id": "stability-" + stability_id,
                        "engine_id": engine_id,
                        "operational_stability_ready": True,
                        "actual_submission_allowed": False,
                        "broker_network_allowed": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }

                    if stability_token_path.exists():
                        existing = _load_json(stability_token_path)
                        if existing.get("stability_id") == token["stability_id"]:
                            duplicate_token = True
                        else:
                            issues.append({
                                "code": "STABILITY_TOKEN_CONFLICT",
                                "blocking": True,
                                "detail": "existing token belongs to another engine",
                            })
                    else:
                        _write_json(stability_token_path, token)
                        token_written = True
        finally:
            if lock_acquired:
                _write_json(process_lock_path, {
                    "stage_range": "V141.01-V141.05",
                    "released": True,
                    "engine_id": engine_id,
                    "released_at": datetime.now(timezone.utc).isoformat(),
                })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        stability_ready = bool(
            required
            and health_ready
            and retry_ready
            and audit_written
            and integrity_verified
            and (token_written or duplicate_token)
            and not safe_mode
        )

        if safe_mode:
            state, status = "OPERATIONAL_STABILITY_SAFE_MODE", "BLOCKED"
        elif stability_ready:
            state, status = "PAPER_RUNTIME_STABILITY_READY", "PASS"
        else:
            state, status = "WAIT_PAPER_INTEGRATION", "PASS"

        result = {
            "stage_range": "V141.01-V141.05",
            "implementation_type": "ULTRA_FAST_OPERATIONAL_STABILITY_BUNDLE",
            "status": status,
            "state": state,
            "engine_id": engine_id,
            "daily_audit_written": audit_written,
            "process_lock_verified": bool(lock_acquired or not required),
            "retry_policy_ready": retry_ready,
            "ledger_integrity_verified": integrity_verified,
            "operational_health_ready": health_ready,
            "operational_stability_ready": stability_ready,
            "stability_token_written": token_written,
            "duplicate_stability_token": duplicate_token,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "V141_06_TO_V141_08"
                if stability_ready
                else "V141_01_TO_V141_05_WAIT_PAPER_INTEGRATION"
            ),
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "validation_mode": "LOCAL_OPERATIONAL_STABILITY_ONLY",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "result_path": str(result_path.resolve()),
        }
        _write_json(result_path, result)
        return result
