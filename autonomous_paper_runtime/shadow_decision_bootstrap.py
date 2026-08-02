from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_ACTIONS = {"BUY", "SELL", "HOLD"}


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _decision_id(session_id: str, symbol: str, action: str, as_of: str) -> str:
    raw = f"{session_id}|{symbol}|{action}|{as_of}"
    return "shadow-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class ShadowDecisionBootstrap:
    def run(
        self,
        *,
        scheduled_result_path: Path,
        shadow_policy_path: Path,
        signal_snapshot_path: Path,
        portfolio_snapshot_path: Path,
        shadow_decision_path: Path,
        risk_report_path: Path,
        shadow_ledger_path: Path,
        shadow_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            scheduled = _load(scheduled_result_path)
        except Exception as exc:
            scheduled = {}
            issues.append({
                "code": "INVALID_SCHEDULED_COLLECTION_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not scheduled:
            issues.append({
                "code": "SCHEDULED_COLLECTION_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(scheduled_result_path),
            })

        source_status = str(scheduled.get("status", "")).upper()
        source_state = str(scheduled.get("state", "")).upper()
        source_safe = bool(scheduled.get("safe_mode_engaged", False))
        schedule_ready = bool(
            scheduled.get("windows_scheduled_collection_ready", False)
        )
        schedule_id = str(scheduled.get("schedule_id", "")).strip()
        pilot_id = str(scheduled.get("pilot_id", "")).strip()

        if source_status == "BLOCKED" or source_safe:
            issues.append({
                "code": "SOURCE_SCHEDULED_COLLECTION_SAFE_MODE",
                "blocking": True,
                "detail": source_state,
            })

        required = (
            schedule_ready
            or source_state == "WINDOWS_SCHEDULED_READ_ONLY_PLAN_READY"
        )

        policy: dict[str, Any] = {}
        signal: dict[str, Any] = {}
        portfolio: dict[str, Any] = {}

        if required:
            for name, path in (
                ("SHADOW_POLICY", shadow_policy_path),
                ("SIGNAL_SNAPSHOT", signal_snapshot_path),
                ("PORTFOLIO_SNAPSHOT", portfolio_snapshot_path),
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

                if name == "SHADOW_POLICY":
                    policy = loaded
                elif name == "SIGNAL_SNAPSHOT":
                    signal = loaded
                else:
                    portfolio = loaded

        policy_ready = False
        shadow_session_id = ""
        if policy:
            shadow_session_id = str(
                policy.get("shadow_session_id", "")
            ).strip()
            checks = [
                ("SHADOW_SESSION_ID_MISSING", bool(shadow_session_id)),
                ("SHADOW_MODE_REQUIRED", bool(policy.get("shadow_mode", False))),
                (
                    "ORDER_SUBMISSION_MUST_BE_DISABLED",
                    not bool(policy.get("order_submission_enabled", True)),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
                (
                    "BROKER_WRITE_MUST_BE_DISABLED",
                    not bool(policy.get("broker_write_enabled", True)),
                ),
                (
                    "MAX_SHADOW_NOTIONAL_INVALID",
                    0 < float(policy.get("max_shadow_notional", 0)) <= 100000,
                ),
                (
                    "MAX_SHADOW_QUANTITY_INVALID",
                    1 <= int(policy.get("max_shadow_quantity", 0)) <= 10000,
                ),
                (
                    "MIN_CONFIDENCE_INVALID",
                    0 <= float(policy.get("minimum_confidence", -1)) <= 1,
                ),
                (
                    "ALLOWED_ACTIONS_INVALID",
                    set(policy.get("allowed_actions", [])) == VALID_ACTIONS,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "shadow policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        signal_ready = False
        symbol = ""
        action = ""
        confidence = 0.0
        reference_price = 0.0
        requested_quantity = 0
        as_of = ""

        if signal:
            symbol = str(signal.get("symbol", "")).upper().strip()
            action = str(signal.get("action", "")).upper().strip()
            confidence = float(signal.get("confidence", 0))
            reference_price = float(signal.get("reference_price", 0))
            requested_quantity = int(signal.get("quantity", 0))
            as_of = str(signal.get("as_of", "")).strip()

            checks = [
                ("SYMBOL_MISSING", bool(symbol)),
                ("INVALID_SHADOW_ACTION", action in VALID_ACTIONS),
                ("INVALID_CONFIDENCE", 0 <= confidence <= 1),
                ("INVALID_REFERENCE_PRICE", reference_price > 0),
                ("INVALID_QUANTITY", requested_quantity >= 0),
                ("SIGNAL_TIMESTAMP_MISSING", bool(as_of)),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "shadow signal validation failed",
                    })
            signal_ready = all(passed for _, passed in checks)

        portfolio_ready = False
        if portfolio:
            account = dict(portfolio.get("account", {}))
            positions = list(portfolio.get("positions", []))
            open_orders = list(portfolio.get("open_orders", []))
            checks = [
                (
                    "ACCOUNT_NOT_ACTIVE",
                    str(account.get("status", "")).upper() == "ACTIVE",
                ),
                (
                    "ACCOUNT_BLOCKED",
                    not bool(account.get("account_blocked", False)),
                ),
                (
                    "TRADING_BLOCKED",
                    not bool(account.get("trading_blocked", False)),
                ),
                (
                    "POSITIONS_NOT_LIST",
                    isinstance(positions, list),
                ),
                (
                    "OPEN_ORDERS_NOT_LIST",
                    isinstance(open_orders, list),
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "portfolio snapshot validation failed",
                    })
            portfolio_ready = all(passed for _, passed in checks)

        risk_approved = False
        approved_action = "HOLD"
        approved_quantity = 0
        shadow_notional = 0.0
        risk_reasons: list[str] = []

        if policy_ready and signal_ready and portfolio_ready:
            if confidence < float(policy["minimum_confidence"]):
                risk_reasons.append("CONFIDENCE_BELOW_MINIMUM")
            elif action == "HOLD":
                approved_action = "HOLD"
                approved_quantity = 0
                risk_approved = True
            else:
                approved_quantity = min(
                    requested_quantity,
                    int(policy["max_shadow_quantity"]),
                )
                shadow_notional = approved_quantity * reference_price

                if approved_quantity <= 0:
                    risk_reasons.append("ZERO_APPROVED_QUANTITY")
                if shadow_notional > float(policy["max_shadow_notional"]):
                    risk_reasons.append("SHADOW_NOTIONAL_LIMIT_EXCEEDED")

                existing_symbols = {
                    str(item.get("symbol", "")).upper()
                    for item in portfolio.get("positions", [])
                    if isinstance(item, dict)
                }
                open_order_symbols = {
                    str(item.get("symbol", "")).upper()
                    for item in portfolio.get("open_orders", [])
                    if isinstance(item, dict)
                }

                if action == "BUY" and symbol in existing_symbols:
                    risk_reasons.append("EXISTING_POSITION_PRESENT")
                if symbol in open_order_symbols:
                    risk_reasons.append("OPEN_ORDER_PRESENT")

                if not risk_reasons:
                    approved_action = action
                    risk_approved = True

        decision_id = ""
        duplicate_signal = False
        decision_written = False
        risk_written = False
        ledger_written = False
        token_written = False
        duplicate_token = False

        blocking_before_decision = sum(
            1 for issue in issues if issue.get("blocking")
        )
        decision_ready = bool(
            required
            and policy_ready
            and signal_ready
            and portfolio_ready
            and blocking_before_decision == 0
        )

        now = datetime.now(timezone.utc).isoformat()

        if decision_ready:
            decision_id = _decision_id(
                shadow_session_id,
                symbol,
                action,
                as_of,
            )

            existing_records: list[dict[str, Any]] = []
            if shadow_ledger_path.exists():
                for line in shadow_ledger_path.read_text(
                    encoding="utf-8"
                ).splitlines():
                    if line.strip():
                        item = json.loads(line)
                        if isinstance(item, dict):
                            existing_records.append(item)

            duplicate_signal = any(
                item.get("decision_id") == decision_id
                for item in existing_records
            )

            if duplicate_signal:
                issues.append({
                    "code": "DUPLICATE_SHADOW_SIGNAL",
                    "blocking": True,
                    "detail": decision_id,
                })
            else:
                decision_payload = {
                    "stage": "OP2.01",
                    "decision_id": decision_id,
                    "shadow_session_id": shadow_session_id,
                    "pilot_id": pilot_id,
                    "schedule_id": schedule_id,
                    "symbol": symbol,
                    "requested_action": action,
                    "approved_action": (
                        approved_action if risk_approved else "HOLD"
                    ),
                    "confidence": confidence,
                    "reference_price": reference_price,
                    "requested_quantity": requested_quantity,
                    "approved_quantity": (
                        approved_quantity if risk_approved else 0
                    ),
                    "shadow_notional": (
                        shadow_notional if risk_approved else 0
                    ),
                    "shadow_only": True,
                    "order_submission_attempted": False,
                    "created_at": now,
                }
                _write(shadow_decision_path, decision_payload)
                decision_written = True

                risk_payload = {
                    "stage": "OP2.02",
                    "decision_id": decision_id,
                    "risk_approved": risk_approved,
                    "risk_reasons": risk_reasons,
                    "approved_action": (
                        approved_action if risk_approved else "HOLD"
                    ),
                    "approved_quantity": (
                        approved_quantity if risk_approved else 0
                    ),
                    "created_at": now,
                }
                _write(risk_report_path, risk_payload)
                risk_written = True

                ledger_payload = {
                    "stage": "OP2.03",
                    "decision_id": decision_id,
                    "shadow_session_id": shadow_session_id,
                    "symbol": symbol,
                    "action": (
                        approved_action if risk_approved else "HOLD"
                    ),
                    "quantity": (
                        approved_quantity if risk_approved else 0
                    ),
                    "reference_price": reference_price,
                    "risk_approved": risk_approved,
                    "shadow_only": True,
                    "paper_order_submitted": False,
                    "live_order_submitted": False,
                    "created_at": now,
                }
                _append_jsonl(shadow_ledger_path, ledger_payload)
                ledger_written = True

                token_payload = {
                    "stage": "OP2.04",
                    "decision_id": decision_id,
                    "shadow_session_id": shadow_session_id,
                    "shadow_decision_ready": True,
                    "risk_approved": risk_approved,
                    "approved_action": (
                        approved_action if risk_approved else "HOLD"
                    ),
                    "order_submission_enabled": False,
                    "broker_write_enabled": False,
                    "live_trading_enabled": False,
                    "created_at": now,
                }

                if shadow_token_path.exists():
                    existing_token = _load(shadow_token_path)
                    if existing_token.get("decision_id") == decision_id:
                        duplicate_token = True
                    else:
                        issues.append({
                            "code": "SHADOW_TOKEN_CONFLICT",
                            "blocking": True,
                            "detail": "another decision owns the token",
                        })
                else:
                    _write(shadow_token_path, token_payload)
                    token_written = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0

        shadow_ready = bool(
            decision_ready
            and not duplicate_signal
            and decision_written
            and risk_written
            and ledger_written
            and (token_written or duplicate_token)
            and not safe_mode
        )

        if safe_mode:
            out_state, out_status = "SHADOW_DECISION_SAFE_MODE", "BLOCKED"
        elif shadow_ready:
            out_state, out_status = "SHADOW_DECISION_READY", "PASS"
        else:
            out_state, out_status = "WAIT_WINDOWS_SCHEDULED_COLLECTION", "PASS"

        result = {
            "stage_range": "OP2.01-OP2.04",
            "implementation_type": "SHADOW_DECISION_BOOTSTRAP",
            "status": out_status,
            "state": out_state,
            "pilot_id": pilot_id,
            "schedule_id": schedule_id,
            "shadow_session_id": shadow_session_id,
            "decision_id": decision_id,
            "symbol": symbol,
            "requested_action": action,
            "approved_action": (
                approved_action if risk_approved else "HOLD"
            ),
            "confidence": confidence,
            "requested_quantity": requested_quantity,
            "approved_quantity": (
                approved_quantity if risk_approved else 0
            ),
            "shadow_notional": (
                shadow_notional if risk_approved else 0
            ),
            "policy_ready": policy_ready,
            "signal_ready": signal_ready,
            "portfolio_ready": portfolio_ready,
            "risk_approved": risk_approved,
            "risk_reasons": risk_reasons,
            "duplicate_signal": duplicate_signal,
            "shadow_decision_written": decision_written,
            "risk_report_written": risk_written,
            "shadow_ledger_written": ledger_written,
            "shadow_token_written": token_written,
            "duplicate_shadow_token": duplicate_token,
            "shadow_decision_ready": shadow_ready,
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
                "OP2_05_SHADOW_PERFORMANCE_EVALUATION"
                if shadow_ready
                else "OP2_01_TO_OP2_04_WAIT_SCHEDULE"
            ),
            "validation_mode": "LOCAL_SHADOW_DECISION_ONLY",
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
