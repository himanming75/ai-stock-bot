
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def deterministic_id(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:20]}"


def evaluate_authorization(
    *,
    signal: dict[str, Any],
    risk_result: dict[str, Any],
    policy: dict[str, Any],
    market_session_open: bool,
) -> dict[str, Any]:
    action = str(signal.get("shadow_action", "HOLD")).upper()
    symbol = str(signal.get("symbol", "")).upper()
    quantity = int(signal.get("quantity", 0) or 0)

    reasons: list[str] = []
    authorized = False

    if bool(risk_result.get("kill_switch_active", False)):
        reasons.append("KILL_SWITCH_ACTIVE")
    if bool(risk_result.get("recovery_lock_active", False)):
        reasons.append("RECOVERY_LOCK_ACTIVE")
    if str(risk_result.get("state", "")) != "SHADOW_RISK_CLEAR":
        reasons.append("RISK_STATE_NOT_CLEAR")
    if not market_session_open and action in {"BUY", "SELL"}:
        reasons.append("MARKET_SESSION_CLOSED")

    blocked_symbols = {
        str(item).upper()
        for item in policy.get("blocked_symbols", [])
    }
    if symbol and symbol in blocked_symbols:
        reasons.append("SYMBOL_BLOCKED")

    allowed_actions = {
        str(item).upper()
        for item in policy.get("allowed_actions", ["BUY", "SELL", "HOLD"])
    }
    if action not in allowed_actions:
        reasons.append("ACTION_NOT_ALLOWED")

    maximum_quantity = int(policy.get("maximum_quantity", 100))
    if quantity < 0:
        reasons.append("NEGATIVE_QUANTITY")
    if quantity > maximum_quantity:
        reasons.append("MAXIMUM_QUANTITY_EXCEEDED")

    if action in {"BUY", "SELL"}:
        if not symbol:
            reasons.append("SYMBOL_REQUIRED")
        if quantity <= 0:
            reasons.append("POSITIVE_QUANTITY_REQUIRED")
    elif action == "HOLD":
        quantity = 0

    if not reasons:
        authorized = True

    decision = (
        "AUTHORIZED"
        if authorized and action in {"BUY", "SELL"}
        else "NO_ACTION"
        if authorized and action == "HOLD"
        else "REJECTED"
    )

    return {
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "authorized": authorized,
        "decision": decision,
        "authorization_reasons": reasons,
    }


def run_shadow_trade_authorization(
    *,
    signal_path: Path,
    risk_result_path: Path,
    policy_path: Path,
    authorization_ledger_path: Path,
    authorization_snapshot_path: Path,
    dashboard_path: Path,
    result_path: Path,
    market_session_open: bool = True,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    try:
        signal = load_json(signal_path)
    except Exception as exc:
        signal = {}
        issues.append({
            "code": "INVALID_SHADOW_SIGNAL",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        risk_result = load_json(risk_result_path)
    except Exception as exc:
        risk_result = {}
        issues.append({
            "code": "INVALID_RISK_RESULT",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_AUTHORIZATION_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "AUTHORIZATION_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    safety_checks = (
        ("SHADOW_ONLY_REQUIRED", bool(policy.get("shadow_only", False))),
        (
            "BROKER_WRITE_MUST_BE_DISABLED",
            not bool(policy.get("broker_write_enabled", True)),
        ),
        (
            "ORDER_SUBMISSION_MUST_BE_DISABLED",
            not bool(policy.get("order_submission_enabled", True)),
        ),
        (
            "LIVE_TRADING_MUST_BE_DISABLED",
            not bool(policy.get("live_trading_enabled", True)),
        ),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "authorization safety policy failed",
            })

    blocking = any(item.get("blocking") for item in issues)

    if blocking:
        decision = {
            "symbol": "",
            "action": "HOLD",
            "quantity": 0,
            "authorized": False,
            "decision": "REJECTED",
            "authorization_reasons": [
                "AUTHORIZATION_INPUT_OR_POLICY_BLOCKED"
            ],
        }
    else:
        decision = evaluate_authorization(
            signal=signal,
            risk_result=risk_result,
            policy=policy,
            market_session_open=market_session_open,
        )

    now = datetime.now(timezone.utc).isoformat()
    authorization_seed = {
        "symbol": decision["symbol"],
        "action": decision["action"],
        "quantity": decision["quantity"],
        "decision": decision["decision"],
        "signal_observed_at": signal.get("observed_at", ""),
        "authorized_at": now,
    }
    authorization_id = deterministic_id(
        "shadow-authorization",
        authorization_seed,
    )

    ledger_record = {
        "stage": "V82.17-V82.19",
        "authorization_id": authorization_id,
        **decision,
        "market_session_open": market_session_open,
        "risk_state": risk_result.get("state", ""),
        "kill_switch_active": bool(
            risk_result.get("kill_switch_active", False)
        ),
        "recovery_lock_active": bool(
            risk_result.get("recovery_lock_active", False)
        ),
        "broker_action_performed": False,
        "authorized_at": now,
    }
    append_jsonl(authorization_ledger_path, ledger_record)

    snapshot = {
        "stage": "V82.19",
        "authorization_id": authorization_id,
        **decision,
        "market_session_open": market_session_open,
        "risk_state": risk_result.get("state", ""),
        "kill_switch_active": bool(
            risk_result.get("kill_switch_active", False)
        ),
        "recovery_lock_active": bool(
            risk_result.get("recovery_lock_active", False)
        ),
        "shadow_only": True,
        "observed_at": now,
    }
    write_json(authorization_snapshot_path, snapshot)

    if blocking:
        state, status = "SHADOW_AUTHORIZATION_SAFE_MODE", "BLOCKED"
    elif decision["decision"] == "AUTHORIZED":
        state, status = "SHADOW_TRADE_AUTHORIZED", "PASS"
    elif decision["decision"] == "NO_ACTION":
        state, status = "SHADOW_TRADE_NO_ACTION", "PASS"
    else:
        state, status = "SHADOW_TRADE_REJECTED", "PASS"

    dashboard = {
        "stage": "V82.20",
        "authorization_state": state,
        "authorization_id": authorization_id,
        "symbol": decision["symbol"],
        "action": decision["action"],
        "quantity": decision["quantity"],
        "authorized": decision["authorized"],
        "decision": decision["decision"],
        "authorization_reasons": decision[
            "authorization_reasons"
        ],
        "risk_state": risk_result.get("state", ""),
        "kill_switch_active": bool(
            risk_result.get("kill_switch_active", False)
        ),
        "recovery_lock_active": bool(
            risk_result.get("recovery_lock_active", False)
        ),
        "read_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.17-V82.20",
        "implementation_type": "SHADOW_TRADE_AUTHORIZATION",
        "status": status,
        "state": state,
        "authorization_id": authorization_id,
        **decision,
        "market_session_open": market_session_open,
        "risk_state": risk_result.get("state", ""),
        "kill_switch_active": bool(
            risk_result.get("kill_switch_active", False)
        ),
        "recovery_lock_active": bool(
            risk_result.get("recovery_lock_active", False)
        ),
        "authorization_ledger_written": True,
        "authorization_snapshot_written": True,
        "dashboard_state_written": True,
        "shadow_only": True,
        "paper_only": True,
        "read_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "cancel_enabled": False,
        "replace_enabled": False,
        "position_close_enabled": False,
        "live_trading_enabled": False,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "issue_count": len(issues),
        "blocking_issue_count": sum(
            1 for item in issues if item.get("blocking")
        ),
        "issues": issues,
        "next_phase": (
            "V82_21_PAPER_TRADING_SESSION_MANAGER"
            if state in {
                "SHADOW_TRADE_AUTHORIZED",
                "SHADOW_TRADE_NO_ACTION",
                "SHADOW_TRADE_REJECTED",
            }
            else "V82_17_TO_V82_20_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_SHADOW_AUTHORIZATION_ONLY",
        "observed_at": now,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
