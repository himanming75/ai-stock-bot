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
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _stable_id(prefix: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


class ControlledPaperPilotFoundation:
    def run(
        self,
        *,
        policy_path: Path,
        current_snapshot_path: Path,
        lifecycle_result_path: Path,
        limited_runtime_result_path: Path,
        pilot_registry_path: Path,
        pilot_lock_path: Path,
        pilot_session_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
        start_pilot: bool = False,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        loaded: dict[str, dict[str, Any]] = {}
        for name, path, required in (
            ("PILOT_POLICY", policy_path, True),
            ("CURRENT_PAPER_SNAPSHOT", current_snapshot_path, True),
            ("LIFECYCLE_RESULT", lifecycle_result_path, False),
            ("LIMITED_RUNTIME_RESULT", limited_runtime_result_path, False),
        ):
            try:
                payload = _load(path)
            except Exception as exc:
                payload = {}
                issues.append({
                    "code": f"INVALID_{name}",
                    "blocking": True,
                    "detail": str(exc),
                })
            if required and not payload:
                issues.append({
                    "code": f"{name}_NOT_FOUND",
                    "blocking": True,
                    "detail": str(path),
                })
            loaded[name] = payload

        policy = loaded["PILOT_POLICY"]
        snapshot = loaded["CURRENT_PAPER_SNAPSHOT"]
        lifecycle = loaded["LIFECYCLE_RESULT"]
        runtime = loaded["LIMITED_RUNTIME_RESULT"]

        pilot_name = ""
        policy_ready = False
        if policy:
            pilot_name = str(policy.get("pilot_name", "")).strip()
            checks = [
                ("PILOT_NAME_MISSING", bool(pilot_name)),
                (
                    "PAPER_ONLY_REQUIRED",
                    bool(policy.get("paper_only", False)),
                ),
                (
                    "SINGLE_PILOT_ONLY_REQUIRED",
                    bool(policy.get("single_pilot_only", False)),
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
                    "AUTOMATIC_ORDER_SUBMISSION_MUST_BE_DISABLED",
                    not bool(
                        policy.get(
                            "automatic_order_submission_enabled",
                            True,
                        )
                    ),
                ),
                (
                    "OPEN_ORDER_CLEARANCE_REQUIRED",
                    bool(
                        policy.get(
                            "require_zero_open_orders",
                            False,
                        )
                    ),
                ),
                (
                    "MAX_PILOT_DAYS_INVALID",
                    1
                    <= int(policy.get("maximum_pilot_days", 0))
                    <= 60,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "pilot policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        snapshot_actual = bool(
            snapshot.get("snapshot_type")
            == "ACTUAL_ALPACA_PAPER_READ_ONLY"
            and snapshot.get("paper_only") is True
            and snapshot.get("read_only") is True
        )
        if snapshot and not snapshot_actual:
            issues.append({
                "code": "ACTUAL_PAPER_SNAPSHOT_REQUIRED",
                "blocking": True,
                "detail": str(snapshot.get("snapshot_type", "")),
            })

        account = snapshot.get("account", {})
        if not isinstance(account, dict):
            account = {}
        positions = snapshot.get("positions", [])
        if not isinstance(positions, list):
            positions = []
        open_orders = snapshot.get("open_orders", [])
        if not isinstance(open_orders, list):
            open_orders = []

        account_ready = bool(
            str(account.get("status", "")).upper() == "ACTIVE"
            and not bool(account.get("account_blocked", False))
            and not bool(account.get("trading_blocked", False))
        )
        if snapshot and not account_ready:
            issues.append({
                "code": "PAPER_ACCOUNT_NOT_READY",
                "blocking": True,
                "detail": str(account.get("status", "")),
            })

        open_order_count = len(open_orders)
        open_orders_clear = open_order_count == 0
        if (
            policy.get("require_zero_open_orders", False)
            and not open_orders_clear
        ):
            issues.append({
                "code": "OPEN_ORDERS_PRESENT",
                "blocking": False,
                "detail": str(open_order_count),
            })

        emergency_stop_engaged = bool(
            runtime.get("safe_mode_engaged", False)
            and any(
                isinstance(item, dict)
                and item.get("code") == "EMERGENCY_STOP"
                for item in runtime.get("issues", [])
            )
        )
        if emergency_stop_engaged:
            issues.append({
                "code": "EMERGENCY_STOP_ENGAGED",
                "blocking": True,
                "detail": "",
            })

        recovery_required = bool(
            lifecycle.get("recovery_required", False)
        )
        if recovery_required:
            issues.append({
                "code": "ORDER_RECOVERY_REQUIRED",
                "blocking": False,
                "detail": str(lifecycle.get("order_status", "")),
            })

        existing_lock = {}
        if pilot_lock_path.exists():
            try:
                existing_lock = _load(pilot_lock_path)
            except Exception as exc:
                issues.append({
                    "code": "INVALID_EXISTING_PILOT_LOCK",
                    "blocking": True,
                    "detail": str(exc),
                })

        duplicate_pilot = bool(
            existing_lock.get("active", False)
        )
        if duplicate_pilot and start_pilot:
            issues.append({
                "code": "DUPLICATE_PILOT_BLOCKED",
                "blocking": True,
                "detail": str(
                    existing_lock.get("pilot_id", "")
                ),
            })

        observed_at = datetime.now(timezone.utc).isoformat()
        seed = (
            f"{pilot_name}|"
            f"{snapshot.get('observed_at', observed_at)}"
        )
        pilot_id = _stable_id("pilot", seed)
        session_id = _stable_id(
            "session", f"{pilot_id}|paper-session"
        )

        blocking = sum(
            1 for issue in issues if issue.get("blocking")
        )

        start_gate_ready = bool(
            policy_ready
            and snapshot_actual
            and account_ready
            and open_orders_clear
            and not emergency_stop_engaged
            and not recovery_required
            and not duplicate_pilot
            and blocking == 0
        )

        pilot_started = False
        lock_written = False
        session_written = False
        registry_written = False

        if start_pilot and start_gate_ready:
            lock_payload = {
                "pilot_id": pilot_id,
                "session_id": session_id,
                "active": True,
                "created_at": observed_at,
                "paper_only": True,
            }
            _write(pilot_lock_path, lock_payload)
            lock_written = True

            _write(pilot_session_path, {
                "stage": "OP4.02",
                "pilot_id": pilot_id,
                "session_id": session_id,
                "pilot_name": pilot_name,
                "status": "RUNNING",
                "started_at": observed_at,
                "maximum_pilot_days": int(
                    policy["maximum_pilot_days"]
                ),
                "open_order_count_at_start": 0,
                "position_count_at_start": len(positions),
                "paper_only": True,
                "broker_write_enabled": False,
                "live_trading_enabled": False,
            })
            session_written = True

            registry = {
                "stage": "OP4.03",
                "active_pilot_id": pilot_id,
                "active_session_id": session_id,
                "pilot_count": 1,
                "last_updated_at": observed_at,
                "paper_only": True,
            }
            _write(pilot_registry_path, registry)
            registry_written = True
            pilot_started = True

        if blocking > 0:
            state, status = (
                "CONTROLLED_PAPER_PILOT_SAFE_MODE",
                "BLOCKED",
            )
        elif pilot_started:
            state, status = (
                "CONTROLLED_PAPER_PILOT_RUNNING",
                "PASS",
            )
        elif not open_orders_clear:
            state, status = (
                "WAIT_OPEN_ORDERS_CLEARANCE",
                "PASS",
            )
        elif recovery_required:
            state, status = (
                "WAIT_ORDER_RECOVERY",
                "PASS",
            )
        elif start_gate_ready:
            state, status = (
                "CONTROLLED_PAPER_PILOT_READY",
                "PASS",
            )
        else:
            state, status = (
                "WAIT_PILOT_PREREQUISITES",
                "PASS",
            )

        dashboard_payload = {
            "stage": "OP4.04",
            "pilot_id": (
                pilot_id if pilot_started else ""
            ),
            "session_id": (
                session_id if pilot_started else ""
            ),
            "pilot_name": pilot_name,
            "pilot_status": (
                "RUNNING"
                if pilot_started
                else "WAITING"
            ),
            "pilot_state": state,
            "start_gate_ready": start_gate_ready,
            "pilot_started": pilot_started,
            "duplicate_pilot": duplicate_pilot,
            "open_order_count": open_order_count,
            "open_orders_clear": open_orders_clear,
            "position_count": len(positions),
            "recovery_required": recovery_required,
            "emergency_stop_engaged": (
                emergency_stop_engaged
            ),
            "paper_account_ready": account_ready,
            "started_at": (
                observed_at if pilot_started else ""
            ),
            "paper_only": True,
            "read_only_dashboard": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": observed_at,
        }
        _write(dashboard_state_path, dashboard_payload)

        result = {
            "stage_range": "OP4.01-OP4.04",
            "implementation_type": (
                "CONTROLLED_PAPER_PILOT_FOUNDATION"
            ),
            "status": status,
            "state": state,
            "pilot_name": pilot_name,
            "pilot_id": (
                pilot_id if pilot_started else ""
            ),
            "session_id": (
                session_id if pilot_started else ""
            ),
            "start_pilot_requested": start_pilot,
            "start_gate_ready": start_gate_ready,
            "pilot_started": pilot_started,
            "pilot_lock_written": lock_written,
            "pilot_session_written": session_written,
            "pilot_registry_written": registry_written,
            "dashboard_state_written": True,
            "duplicate_pilot": duplicate_pilot,
            "open_order_count": open_order_count,
            "open_orders_clear": open_orders_clear,
            "position_count": len(positions),
            "recovery_required": recovery_required,
            "emergency_stop_engaged": (
                emergency_stop_engaged
            ),
            "paper_account_ready": account_ready,
            "paper_only": True,
            "broker_write_enabled": False,
            "automatic_order_submission_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": blocking > 0,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "OP4_05_PAPER_SESSION_MONITOR"
                if pilot_started
                else "OP4_01_TO_OP4_04_WAIT_START_GATE"
            ),
            "validation_mode": (
                "LOCAL_CONTROLLED_PAPER_PILOT_FOUNDATION"
            ),
            "observed_at": observed_at,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
