from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"
APPROVAL_PHRASE = "APPROVE OP3 LIMITED AUTONOMOUS PAPER CYCLE"


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


def _append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _client_order_id(runtime_id: str, signal_id: str, symbol: str, cycle_date: str) -> str:
    raw = f"{runtime_id}|{signal_id}|{symbol}|{cycle_date}"
    return "op3auto-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _default_post(
    *,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout_seconds: int,
) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            return int(response.status), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"message": raw}
        return int(exc.code), payload


class LimitedAutonomousPaperTrading:
    def run(
        self,
        *,
        lifecycle_result_path: Path,
        runtime_policy_path: Path,
        signal_snapshot_path: Path,
        risk_snapshot_path: Path,
        account_snapshot_path: Path,
        runtime_state_path: Path,
        decision_path: Path,
        submission_receipt_path: Path,
        runtime_ledger_path: Path,
        completion_token_path: Path,
        result_path: Path,
        enable_network: bool = False,
        enable_submission: bool = False,
        approval_phrase: str = "",
        base_url: str = PAPER_BASE_URL,
        transport: Callable[..., tuple[int, dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        loaded: dict[str, dict[str, Any]] = {}
        for name, path in (
            ("LIFECYCLE_RESULT", lifecycle_result_path),
            ("RUNTIME_POLICY", runtime_policy_path),
            ("SIGNAL_SNAPSHOT", signal_snapshot_path),
            ("RISK_SNAPSHOT", risk_snapshot_path),
            ("ACCOUNT_SNAPSHOT", account_snapshot_path),
        ):
            try:
                payload = _load(path)
            except Exception as exc:
                payload = {}
                issues.append({"code": f"INVALID_{name}", "blocking": True, "detail": str(exc)})
            if not payload:
                issues.append({"code": f"{name}_NOT_FOUND", "blocking": True, "detail": str(path)})
            loaded[name] = payload

        lifecycle = loaded["LIFECYCLE_RESULT"]
        policy = loaded["RUNTIME_POLICY"]
        signal = loaded["SIGNAL_SNAPSHOT"]
        risk = loaded["RISK_SNAPSHOT"]
        account = loaded["ACCOUNT_SNAPSHOT"]

        lifecycle_ready = bool(lifecycle.get("paper_order_lifecycle_ready", False))
        lifecycle_terminal = bool(lifecycle.get("lifecycle_complete", False))
        if lifecycle and not lifecycle_ready:
            issues.append({"code": "PRIOR_LIFECYCLE_NOT_READY", "blocking": True, "detail": str(lifecycle.get("state", ""))})
        if lifecycle and not lifecycle_terminal:
            issues.append({"code": "PRIOR_ORDER_STILL_OPEN", "blocking": True, "detail": str(lifecycle.get("order_status", ""))})
        if lifecycle.get("safe_mode_engaged"):
            issues.append({"code": "PRIOR_LIFECYCLE_SAFE_MODE", "blocking": True, "detail": ""})

        endpoint_verified = base_url.rstrip("/") == PAPER_BASE_URL
        if not endpoint_verified:
            issues.append({"code": "LIVE_OR_UNKNOWN_ENDPOINT_BLOCKED", "blocking": True, "detail": base_url})

        runtime_id = ""
        policy_ready = False
        if policy:
            runtime_id = str(policy.get("runtime_id", "")).strip()
            checks = [
                ("RUNTIME_ID_MISSING", bool(runtime_id)),
                ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
                ("SINGLE_CYCLE_ONLY_REQUIRED", bool(policy.get("single_cycle_only", False))),
                ("CONTINUOUS_LOOP_MUST_BE_DISABLED", not bool(policy.get("continuous_loop_enabled", True))),
                ("MAX_ORDERS_PER_CYCLE_INVALID", int(policy.get("maximum_orders_per_cycle", 0)) == 1),
                ("MAX_DAILY_ORDERS_INVALID", 1 <= int(policy.get("maximum_daily_orders", 0)) <= 3),
                ("MAX_NOTIONAL_INVALID", 0 < float(policy.get("maximum_order_notional", 0)) <= 100),
                ("MAX_POSITIONS_INVALID", 1 <= int(policy.get("maximum_open_positions", 0)) <= 3),
                ("MAX_DAILY_LOSS_INVALID", 0 < float(policy.get("maximum_daily_loss", 0)) <= 100),
                ("MAX_CONSECUTIVE_LOSSES_INVALID", 1 <= int(policy.get("maximum_consecutive_losses", 0)) <= 3),
                ("CLOSE_BUFFER_INVALID", 1 <= int(policy.get("market_close_buffer_minutes", 0)) <= 60),
                ("TIMEOUT_INVALID", 3 <= int(policy.get("timeout_seconds", 0)) <= 30),
                ("LIVE_TRADING_MUST_BE_DISABLED", not bool(policy.get("live_trading_enabled", True))),
                ("EXPECTED_ENDPOINT_INVALID", str(policy.get("expected_base_url", "")).rstrip("/") == PAPER_BASE_URL),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({"code": code, "blocking": True, "detail": "runtime policy gate failed"})
            policy_ready = all(passed for _, passed in checks)

        signal_ready = False
        signal_id = ""
        symbol = ""
        action = ""
        confidence = 0.0
        quantity = 0
        reference_price = 0.0
        if signal:
            signal_id = str(signal.get("signal_id", "")).strip()
            symbol = str(signal.get("symbol", "")).upper().strip()
            action = str(signal.get("approved_action", "")).upper().strip()
            confidence = float(signal.get("confidence", 0))
            quantity = int(signal.get("quantity", 0))
            reference_price = float(signal.get("reference_price", 0))
            checks = [
                ("SIGNAL_ID_MISSING", bool(signal_id)),
                ("SIGNAL_SYMBOL_MISSING", bool(symbol)),
                ("SIGNAL_ACTION_INVALID", action in {"BUY", "SELL", "HOLD"}),
                ("SIGNAL_CONFIDENCE_INVALID", 0 <= confidence <= 1),
                ("SIGNAL_QUANTITY_INVALID", quantity >= 0),
                ("SIGNAL_REFERENCE_PRICE_INVALID", reference_price > 0),
                ("SIGNAL_NOT_VERIFIED", bool(signal.get("signal_verified", False))),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({"code": code, "blocking": True, "detail": "signal gate failed"})
            signal_ready = all(passed for _, passed in checks)

        risk_ready = False
        risk_reasons: list[str] = []
        if risk and policy_ready and signal_ready:
            daily_orders = int(risk.get("daily_orders", 0))
            open_positions = int(risk.get("open_positions", 0))
            daily_pnl = float(risk.get("daily_pnl", 0))
            consecutive_losses = int(risk.get("consecutive_losses", 0))
            minutes_to_close = int(risk.get("minutes_to_market_close", 0))
            emergency_stop = bool(risk.get("emergency_stop_engaged", False))
            duplicate_signal = bool(risk.get("duplicate_signal", False))
            market_open = bool(risk.get("market_open", False))
            estimated_notional = quantity * reference_price

            if not market_open:
                risk_reasons.append("MARKET_CLOSED")
            if minutes_to_close <= int(policy["market_close_buffer_minutes"]):
                risk_reasons.append("MARKET_CLOSE_BUFFER")
            if daily_orders >= int(policy["maximum_daily_orders"]):
                risk_reasons.append("DAILY_ORDER_LIMIT")
            if open_positions >= int(policy["maximum_open_positions"]) and action == "BUY":
                risk_reasons.append("OPEN_POSITION_LIMIT")
            if daily_pnl <= -float(policy["maximum_daily_loss"]):
                risk_reasons.append("DAILY_LOSS_LIMIT")
            if consecutive_losses >= int(policy["maximum_consecutive_losses"]):
                risk_reasons.append("CONSECUTIVE_LOSS_LIMIT")
            if estimated_notional > float(policy["maximum_order_notional"]):
                risk_reasons.append("ORDER_NOTIONAL_LIMIT")
            if emergency_stop:
                risk_reasons.append("EMERGENCY_STOP")
            if duplicate_signal:
                risk_reasons.append("DUPLICATE_SIGNAL")
            if action in {"BUY", "SELL"} and quantity <= 0:
                risk_reasons.append("ZERO_QUANTITY")
            risk_ready = not risk_reasons

        account_object = account.get("account", account) if isinstance(account, dict) else {}
        if not isinstance(account_object, dict):
            account_object = {}
        account_ready = bool(
            str(account_object.get("status", "")).upper() == "ACTIVE"
            and not bool(account_object.get("account_blocked", False))
            and not bool(account_object.get("trading_blocked", False))
            and float(account_object.get("buying_power", 0)) >= quantity * reference_price
        )
        if account and not account_ready:
            issues.append({"code": "ACCOUNT_GATE_FAILED", "blocking": True, "detail": str(account_object.get("status", ""))})

        cycle_date = str(risk.get("cycle_date", "")).strip()
        if risk and not cycle_date:
            issues.append({"code": "CYCLE_DATE_MISSING", "blocking": True, "detail": ""})

        client_order_id = _client_order_id(runtime_id, signal_id, symbol, cycle_date) if all(
            [runtime_id, signal_id, symbol, cycle_date]
        ) else ""

        duplicate_runtime = False
        if runtime_ledger_path.exists() and client_order_id:
            for line in runtime_ledger_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                if isinstance(item, dict) and item.get("client_order_id") == client_order_id:
                    duplicate_runtime = True
                    break
        if duplicate_runtime:
            issues.append({"code": "DUPLICATE_RUNTIME_CYCLE", "blocking": True, "detail": client_order_id})

        decision = "HOLD"
        approved_quantity = 0
        if (
            lifecycle_ready and lifecycle_terminal and policy_ready and signal_ready
            and risk_ready and account_ready and not any(i.get("blocking") for i in issues)
        ):
            decision = action
            approved_quantity = quantity if action in {"BUY", "SELL"} else 0

        credentials_configured = bool(
            os.getenv("APCA_API_KEY_ID", "").strip()
            and os.getenv("APCA_API_SECRET_KEY", "").strip()
        )
        approval_verified = approval_phrase == APPROVAL_PHRASE
        submission_requested = bool(enable_network and enable_submission)
        submit_order = bool(
            submission_requested and approval_verified and credentials_configured
            and endpoint_verified and decision in {"BUY", "SELL"}
            and approved_quantity > 0 and not duplicate_runtime
            and not any(i.get("blocking") for i in issues)
        )

        now = datetime.now(timezone.utc).isoformat()
        _write(runtime_state_path, {
            "stage": "OP3.13",
            "runtime_id": runtime_id,
            "cycle_date": cycle_date,
            "single_cycle_only": True,
            "continuous_loop_enabled": False,
            "decision": decision,
            "risk_reasons": risk_reasons,
            "created_at": now,
        })
        _write(decision_path, {
            "stage": "OP3.14",
            "runtime_id": runtime_id,
            "signal_id": signal_id,
            "symbol": symbol,
            "requested_action": action,
            "approved_action": decision,
            "approved_quantity": approved_quantity,
            "confidence": confidence,
            "client_order_id": client_order_id,
            "risk_approved": risk_ready,
            "risk_reasons": risk_reasons,
            "paper_only": True,
            "created_at": now,
        })

        network_requests = write_requests = paper_orders = 0
        response_status = 0
        response_payload: dict[str, Any] = {}
        broker_order_id = ""
        submission_succeeded = False
        receipt_written = token_written = False

        if submit_order:
            poster = transport or _default_post
            headers = {
                "APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"].strip(),
                "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"].strip(),
            }
            network_requests = write_requests = 1
            response_status, response_payload = poster(
                url=PAPER_BASE_URL + "/v2/orders",
                headers=headers,
                body={
                    "symbol": symbol,
                    "qty": str(approved_quantity),
                    "side": decision.lower(),
                    "type": "market",
                    "time_in_force": "day",
                    "client_order_id": client_order_id,
                },
                timeout_seconds=int(policy["timeout_seconds"]),
            )
            submission_succeeded = (
                200 <= response_status < 300
                and bool(str(response_payload.get("id", "")).strip())
            )
            if submission_succeeded:
                paper_orders = 1
                broker_order_id = str(response_payload.get("id", ""))
            else:
                issues.append({
                    "code": "LIMITED_AUTONOMOUS_SUBMISSION_FAILED",
                    "blocking": True,
                    "detail": f"HTTP {response_status}: {response_payload.get('message', '')}",
                })

            _write(submission_receipt_path, {
                "stage": "OP3.15",
                "runtime_id": runtime_id,
                "client_order_id": client_order_id,
                "http_status": response_status,
                "submission_succeeded": submission_succeeded,
                "broker_order_id": broker_order_id,
                "response": response_payload,
                "paper_only": True,
                "created_at": now,
            })
            receipt_written = True

            if submission_succeeded:
                _append(runtime_ledger_path, {
                    "stage": "OP3.16",
                    "runtime_id": runtime_id,
                    "cycle_date": cycle_date,
                    "signal_id": signal_id,
                    "client_order_id": client_order_id,
                    "broker_order_id": broker_order_id,
                    "symbol": symbol,
                    "side": decision.lower(),
                    "quantity": approved_quantity,
                    "paper_only": True,
                    "submitted_at": now,
                })
                _write(completion_token_path, {
                    "stage": "OP3.16",
                    "runtime_id": runtime_id,
                    "client_order_id": client_order_id,
                    "broker_order_id": broker_order_id,
                    "limited_autonomous_paper_cycle_complete": True,
                    "paper_orders_submitted": 1,
                    "live_orders_submitted": 0,
                    "created_at": now,
                })
                token_written = True

        blocking = sum(1 for i in issues if i.get("blocking"))
        safe_mode = blocking > 0

        if safe_mode:
            state, status = "LIMITED_AUTONOMOUS_PAPER_SAFE_MODE", "BLOCKED"
        elif submission_succeeded:
            state, status = "LIMITED_AUTONOMOUS_PAPER_ORDER_SUBMITTED", "PASS"
        elif decision in {"BUY", "SELL"}:
            state, status = "LIMITED_AUTONOMOUS_PAPER_CYCLE_ARMED", "PASS"
        else:
            state, status = "LIMITED_AUTONOMOUS_PAPER_CYCLE_HOLD", "PASS"

        result = {
            "stage_range": "OP3.13-OP3.16",
            "implementation_type": "LIMITED_AUTONOMOUS_PAPER_TRADING",
            "status": status,
            "state": state,
            "runtime_id": runtime_id,
            "cycle_date": cycle_date,
            "signal_id": signal_id,
            "symbol": symbol,
            "requested_action": action,
            "approved_action": decision,
            "approved_quantity": approved_quantity,
            "client_order_id": client_order_id,
            "risk_ready": risk_ready,
            "risk_reasons": risk_reasons,
            "account_ready": account_ready,
            "duplicate_runtime_cycle": duplicate_runtime,
            "credentials_configured": credentials_configured,
            "approval_phrase_verified": approval_verified,
            "enable_network": enable_network,
            "enable_submission": enable_submission,
            "submission_requested": submission_requested,
            "submission_gate_ready": submit_order,
            "response_http_status": response_status,
            "broker_order_id": broker_order_id,
            "submission_succeeded": submission_succeeded,
            "submission_receipt_written": receipt_written,
            "completion_token_written": token_written,
            "single_cycle_only": True,
            "continuous_loop_enabled": False,
            "paper_only": True,
            "live_trading_enabled": False,
            "actual_credentials_used": submit_order,
            "actual_external_network_used": network_requests > 0,
            "network_requests_executed": network_requests,
            "write_requests_executed": write_requests,
            "actual_paper_orders_submitted": paper_orders,
            "live_orders_submitted": 0,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "DASH2_01_PAPER_TRADING_DASHBOARD"
                if submission_succeeded
                else "OP3_13_TO_OP3_16_WAIT_EXPLICIT_CYCLE"
            ),
            "validation_mode": (
                "ACTUAL_ALPACA_PAPER_LIMITED_SINGLE_CYCLE"
                if submission_requested
                else "LOCAL_LIMITED_AUTONOMOUS_PREVIEW_ONLY"
            ),
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
