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
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


class DailyReadOnlyObservation:
    def run(
        self,
        *,
        pilot_result_path: Path,
        current_snapshot_path: Path,
        previous_snapshot_path: Path,
        observation_policy_path: Path,
        account_drift_path: Path,
        order_watch_path: Path,
        position_watch_path: Path,
        daily_report_path: Path,
        observation_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            pilot = _load(pilot_result_path)
        except Exception as exc:
            pilot = {}
            issues.append({
                "code": "INVALID_PILOT_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not pilot:
            issues.append({
                "code": "PILOT_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(pilot_result_path),
            })

        pilot_status = str(pilot.get("status", "")).upper()
        pilot_state = str(pilot.get("state", "")).upper()
        pilot_safe = bool(pilot.get("safe_mode_engaged", False))
        pilot_ready = bool(pilot.get("paper_operations_pilot_ready", False))
        pilot_id = str(pilot.get("pilot_id", "")).strip()

        if pilot_status == "BLOCKED" or pilot_safe:
            issues.append({
                "code": "SOURCE_PILOT_SAFE_MODE",
                "blocking": True,
                "detail": pilot_state,
            })

        required = pilot_ready or pilot_state == "PAPER_OPERATIONS_READ_ONLY_READY"

        policy: dict[str, Any] = {}
        current: dict[str, Any] = {}
        previous: dict[str, Any] = {}

        if required:
            for name, path in (
                ("OBSERVATION_POLICY", observation_policy_path),
                ("CURRENT_SNAPSHOT", current_snapshot_path),
                ("PREVIOUS_SNAPSHOT", previous_snapshot_path),
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

                if name == "OBSERVATION_POLICY":
                    policy = loaded
                elif name == "CURRENT_SNAPSHOT":
                    current = loaded
                else:
                    previous = loaded

        policy_ready = False
        observation_id = ""
        if policy:
            observation_id = str(policy.get("observation_id", "")).strip()
            checks = [
                ("OBSERVATION_ID_MISSING", bool(observation_id)),
                ("READ_ONLY_REQUIRED", bool(policy.get("read_only", False))),
                (
                    "ORDER_SUBMISSION_MUST_BE_DISABLED",
                    not bool(policy.get("order_submission_enabled", True)),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
                (
                    "MAX_ALLOWED_OPEN_ORDERS_INVALID",
                    int(policy.get("max_allowed_open_orders", -1)) >= 0,
                ),
                (
                    "MAX_ALLOWED_POSITIONS_INVALID",
                    int(policy.get("max_allowed_positions", -1)) >= 0,
                ),
                (
                    "MAX_EQUITY_DRIFT_INVALID",
                    float(policy.get("max_abs_equity_drift", -1)) >= 0,
                ),
                (
                    "MAX_CASH_DRIFT_INVALID",
                    float(policy.get("max_abs_cash_drift", -1)) >= 0,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "observation policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        snapshot_ready = False
        account_drift_ready = False
        order_watch_ready = False
        position_watch_ready = False

        equity_drift = 0.0
        cash_drift = 0.0
        open_order_count = 0
        position_count = 0
        unexpected_order_ids: list[str] = []
        unexpected_symbols: list[str] = []

        if current and previous:
            current_account = dict(current.get("account", {}))
            previous_account = dict(previous.get("account", {}))
            current_orders = list(current.get("open_orders", []))
            previous_orders = list(previous.get("open_orders", []))
            current_positions = list(current.get("positions", []))
            previous_positions = list(previous.get("positions", []))

            account_checks = [
                (
                    "ACCOUNT_NOT_ACTIVE",
                    str(current_account.get("status", "")).upper() == "ACTIVE",
                ),
                (
                    "ACCOUNT_BLOCKED",
                    not bool(current_account.get("account_blocked", False)),
                ),
                (
                    "TRADING_BLOCKED",
                    not bool(current_account.get("trading_blocked", False)),
                ),
            ]
            for code, passed in account_checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "current account snapshot failed",
                    })

            current_equity = float(current_account.get("equity", 0))
            previous_equity = float(previous_account.get("equity", 0))
            current_cash = float(current_account.get("cash", 0))
            previous_cash = float(previous_account.get("cash", 0))

            equity_drift = current_equity - previous_equity
            cash_drift = current_cash - previous_cash

            drift_checks = [
                (
                    "EQUITY_DRIFT_EXCEEDED",
                    abs(equity_drift)
                    <= float(policy.get("max_abs_equity_drift", 0)),
                ),
                (
                    "CASH_DRIFT_EXCEEDED",
                    abs(cash_drift)
                    <= float(policy.get("max_abs_cash_drift", 0)),
                ),
            ]
            for code, passed in drift_checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "daily account drift threshold exceeded",
                    })
            account_drift_ready = all(passed for _, passed in drift_checks)

            open_order_count = len(current_orders)
            previous_order_ids = {
                str(item.get("id", ""))
                for item in previous_orders
                if isinstance(item, dict)
            }
            current_order_ids = {
                str(item.get("id", ""))
                for item in current_orders
                if isinstance(item, dict)
            }
            unexpected_order_ids = sorted(
                item
                for item in current_order_ids - previous_order_ids
                if item
            )

            order_checks = [
                (
                    "OPEN_ORDER_LIMIT_EXCEEDED",
                    open_order_count
                    <= int(policy.get("max_allowed_open_orders", 0)),
                ),
                (
                    "UNEXPECTED_OPEN_ORDER_DETECTED",
                    not unexpected_order_ids,
                ),
            ]
            for code, passed in order_checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "open-order watch failed",
                    })
            order_watch_ready = all(passed for _, passed in order_checks)

            position_count = len(current_positions)
            previous_symbols = {
                str(item.get("symbol", ""))
                for item in previous_positions
                if isinstance(item, dict)
            }
            current_symbols = {
                str(item.get("symbol", ""))
                for item in current_positions
                if isinstance(item, dict)
            }
            unexpected_symbols = sorted(
                symbol
                for symbol in current_symbols - previous_symbols
                if symbol
            )

            position_checks = [
                (
                    "POSITION_LIMIT_EXCEEDED",
                    position_count
                    <= int(policy.get("max_allowed_positions", 0)),
                ),
                (
                    "UNEXPECTED_POSITION_DETECTED",
                    not unexpected_symbols,
                ),
            ]
            for code, passed in position_checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "position watch failed",
                    })
            position_watch_ready = all(passed for _, passed in position_checks)

            snapshot_ready = all(passed for _, passed in account_checks)

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        observation_ready = bool(
            required
            and policy_ready
            and snapshot_ready
            and account_drift_ready
            and order_watch_ready
            and position_watch_ready
            and blocking == 0
        )

        now = datetime.now(timezone.utc).isoformat()
        drift_written = order_written = position_written = report_written = False
        token_written = duplicate_token = False

        if required and current:
            _write(account_drift_path, {
                "stage": "OP1.05",
                "pilot_id": pilot_id,
                "observation_id": observation_id,
                "equity_drift": equity_drift,
                "cash_drift": cash_drift,
                "account_drift_ready": account_drift_ready,
                "captured_at": now,
            })
            drift_written = True

            _write(order_watch_path, {
                "stage": "OP1.06",
                "pilot_id": pilot_id,
                "observation_id": observation_id,
                "open_order_count": open_order_count,
                "unexpected_order_ids": unexpected_order_ids,
                "order_watch_ready": order_watch_ready,
                "captured_at": now,
            })
            order_written = True

            _write(position_watch_path, {
                "stage": "OP1.07",
                "pilot_id": pilot_id,
                "observation_id": observation_id,
                "position_count": position_count,
                "unexpected_symbols": unexpected_symbols,
                "position_watch_ready": position_watch_ready,
                "captured_at": now,
            })
            position_written = True

            _write(daily_report_path, {
                "stage": "OP1.08",
                "pilot_id": pilot_id,
                "observation_id": observation_id,
                "market_is_open": bool(current.get("clock", {}).get("is_open", False)),
                "equity_drift": equity_drift,
                "cash_drift": cash_drift,
                "open_order_count": open_order_count,
                "position_count": position_count,
                "read_only": True,
                "order_submission_enabled": False,
                "live_trading_enabled": False,
                "daily_observation_ready": observation_ready,
                "captured_at": now,
            })
            report_written = True

        if observation_ready:
            token = {
                "stage_range": "OP1.05-OP1.08",
                "pilot_id": pilot_id,
                "observation_id": observation_id,
                "daily_read_only_observation_ready": True,
                "read_only": True,
                "order_submission_enabled": False,
                "live_trading_enabled": False,
                "created_at": now,
            }
            if observation_token_path.exists():
                existing = _load(observation_token_path)
                if (
                    existing.get("pilot_id") == pilot_id
                    and existing.get("observation_id") == observation_id
                ):
                    duplicate_token = True
                else:
                    issues.append({
                        "code": "OBSERVATION_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "another observation token exists",
                    })
            else:
                _write(observation_token_path, token)
                token_written = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        final_ready = bool(
            observation_ready
            and drift_written
            and order_written
            and position_written
            and report_written
            and (token_written or duplicate_token)
            and not safe_mode
        )

        if safe_mode:
            state, status = "DAILY_OBSERVATION_SAFE_MODE", "BLOCKED"
        elif final_ready:
            state, status = "DAILY_READ_ONLY_OBSERVATION_READY", "PASS"
        else:
            state, status = "WAIT_PAPER_OPERATIONS_PILOT", "PASS"

        result = {
            "stage_range": "OP1.05-OP1.08",
            "implementation_type": "DAILY_READ_ONLY_OBSERVATION",
            "status": status,
            "state": state,
            "pilot_id": pilot_id,
            "observation_id": observation_id,
            "policy_ready": policy_ready,
            "snapshot_ready": snapshot_ready,
            "account_drift_ready": account_drift_ready,
            "order_watch_ready": order_watch_ready,
            "position_watch_ready": position_watch_ready,
            "daily_read_only_observation_ready": final_ready,
            "account_drift_written": drift_written,
            "order_watch_written": order_written,
            "position_watch_written": position_written,
            "daily_report_written": report_written,
            "observation_token_written": token_written,
            "duplicate_observation_token": duplicate_token,
            "equity_drift": equity_drift,
            "cash_drift": cash_drift,
            "open_order_count": open_order_count,
            "position_count": position_count,
            "read_only": True,
            "order_submission_enabled": False,
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
                "OP1_09_WEEKLY_OBSERVATION_SUMMARY"
                if final_ready
                else "OP1_05_TO_OP1_08_WAIT_PILOT"
            ),
            "validation_mode": "LOCAL_DAILY_OBSERVATION_ONLY",
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
