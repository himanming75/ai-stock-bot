from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"
APPROVAL_PHRASE = "APPROVE OP3 CONTROLLED PAPER ORDER PREPARATION"


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


def _candidate_id(
    preparation_id: str,
    symbol: str,
    side: str,
    quantity: int,
    reference_price: float,
) -> str:
    raw = (
        f"{preparation_id}|{symbol}|{side}|"
        f"{quantity}|{reference_price:.8f}"
    )
    return "paper-candidate-" + hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:24]


class ControlledPaperOrderPreparation:
    def run(
        self,
        *,
        dashboard_result_path: Path,
        preparation_policy_path: Path,
        order_candidate_path: Path,
        account_snapshot_path: Path,
        prepared_order_path: Path,
        risk_report_path: Path,
        approval_gate_path: Path,
        preparation_token_path: Path,
        result_path: Path,
        approval_phrase: str = "",
        base_url: str = PAPER_BASE_URL,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        dashboard = {}
        try:
            dashboard = _load(dashboard_result_path)
        except Exception as exc:
            issues.append({
                "code": "INVALID_DASHBOARD_SNAPSHOT",
                "blocking": True,
                "detail": str(exc),
            })

        if not dashboard:
            issues.append({
                "code": "DASHBOARD_SNAPSHOT_NOT_FOUND",
                "blocking": True,
                "detail": str(dashboard_result_path),
            })

        dashboard_read_only = bool(dashboard.get("read_only", False))
        dashboard_safe = (
            dashboard.get("dashboard_state") == "SAFE_MODE"
            or bool(
                dashboard.get("runtime", {}).get("safe_mode", False)
                if isinstance(dashboard.get("runtime"), dict)
                else False
            )
        )

        if dashboard and not dashboard_read_only:
            issues.append({
                "code": "DASHBOARD_READ_ONLY_CONTRACT_FAILED",
                "blocking": True,
                "detail": "dashboard must remain read-only",
            })
        if dashboard_safe:
            issues.append({
                "code": "DASHBOARD_SAFE_MODE",
                "blocking": True,
                "detail": "dashboard reports safe mode",
            })

        endpoint_verified = base_url.rstrip("/") == PAPER_BASE_URL
        if not endpoint_verified:
            issues.append({
                "code": "LIVE_OR_UNKNOWN_ENDPOINT_BLOCKED",
                "blocking": True,
                "detail": base_url,
            })

        policy = {}
        candidate = {}
        account = {}

        for name, path in (
            ("PREPARATION_POLICY", preparation_policy_path),
            ("ORDER_CANDIDATE", order_candidate_path),
            ("ACCOUNT_SNAPSHOT", account_snapshot_path),
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
            if name == "PREPARATION_POLICY":
                policy = loaded
            elif name == "ORDER_CANDIDATE":
                candidate = loaded
            else:
                account = loaded

        policy_ready = False
        preparation_id = ""
        if policy:
            preparation_id = str(
                policy.get("preparation_id", "")
            ).strip()
            checks = [
                ("PREPARATION_ID_MISSING", bool(preparation_id)),
                (
                    "PAPER_ONLY_REQUIRED",
                    bool(policy.get("paper_only", False)),
                ),
                (
                    "SUBMISSION_MUST_BE_DISABLED",
                    not bool(
                        policy.get("order_submission_enabled", True)
                    ),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
                (
                    "NETWORK_WRITE_MUST_BE_DISABLED",
                    not bool(policy.get("network_write_enabled", True)),
                ),
                (
                    "MAX_NOTIONAL_INVALID",
                    0
                    < float(policy.get("maximum_order_notional", 0))
                    <= 1000,
                ),
                (
                    "MAX_QUANTITY_INVALID",
                    1
                    <= int(policy.get("maximum_order_quantity", 0))
                    <= 100,
                ),
                (
                    "MAX_DAILY_CANDIDATES_INVALID",
                    1
                    <= int(policy.get("maximum_daily_candidates", 0))
                    <= 3,
                ),
                (
                    "MANUAL_APPROVAL_REQUIRED",
                    bool(policy.get("manual_approval_required", False)),
                ),
                (
                    "EXPECTED_ENDPOINT_INVALID",
                    str(policy.get("expected_base_url", "")).rstrip("/")
                    == PAPER_BASE_URL,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "preparation policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        candidate_ready = False
        symbol = ""
        side = ""
        order_type = ""
        time_in_force = ""
        quantity = 0
        reference_price = 0.0
        notional = 0.0

        if candidate:
            symbol = str(candidate.get("symbol", "")).upper().strip()
            side = str(candidate.get("side", "")).lower().strip()
            order_type = str(
                candidate.get("order_type", "")
            ).lower().strip()
            time_in_force = str(
                candidate.get("time_in_force", "")
            ).lower().strip()
            quantity = int(candidate.get("quantity", 0))
            reference_price = float(
                candidate.get("reference_price", 0)
            )
            notional = quantity * reference_price

            checks = [
                ("CANDIDATE_SYMBOL_MISSING", bool(symbol)),
                (
                    "CANDIDATE_SIDE_INVALID",
                    side in {"buy", "sell"},
                ),
                (
                    "CANDIDATE_ORDER_TYPE_INVALID",
                    order_type in {"market", "limit"},
                ),
                (
                    "CANDIDATE_TIME_IN_FORCE_INVALID",
                    time_in_force in {"day"},
                ),
                (
                    "CANDIDATE_QUANTITY_INVALID",
                    quantity > 0,
                ),
                (
                    "CANDIDATE_REFERENCE_PRICE_INVALID",
                    reference_price > 0,
                ),
                (
                    "CANDIDATE_NOT_SHADOW_APPROVED",
                    bool(candidate.get("shadow_approved", False)),
                ),
                (
                    "CANDIDATE_SIGNAL_ID_MISSING",
                    bool(str(candidate.get("signal_id", "")).strip()),
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "order candidate validation failed",
                    })
            candidate_ready = all(passed for _, passed in checks)

        account_ready = False
        if account:
            account_object = (
                account.get("account", account)
                if isinstance(account, dict)
                else {}
            )
            if not isinstance(account_object, dict):
                account_object = {}
            checks = [
                (
                    "ACCOUNT_NOT_ACTIVE",
                    str(account_object.get("status", "")).upper()
                    == "ACTIVE",
                ),
                (
                    "ACCOUNT_BLOCKED",
                    not bool(
                        account_object.get("account_blocked", False)
                    ),
                ),
                (
                    "TRADING_BLOCKED",
                    not bool(
                        account_object.get("trading_blocked", False)
                    ),
                ),
                (
                    "INSUFFICIENT_BUYING_POWER",
                    float(account_object.get("buying_power", 0))
                    >= notional,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "Paper account gate failed",
                    })
            account_ready = all(passed for _, passed in checks)

        risk_approved = False
        risk_reasons: list[str] = []

        if policy_ready and candidate_ready and account_ready:
            if quantity > int(policy["maximum_order_quantity"]):
                risk_reasons.append("QUANTITY_LIMIT_EXCEEDED")
            if notional > float(policy["maximum_order_notional"]):
                risk_reasons.append("NOTIONAL_LIMIT_EXCEEDED")
            if int(candidate.get("daily_candidate_number", 1)) > int(
                policy["maximum_daily_candidates"]
            ):
                risk_reasons.append("DAILY_CANDIDATE_LIMIT_EXCEEDED")
            if bool(candidate.get("duplicate_candidate", False)):
                risk_reasons.append("DUPLICATE_CANDIDATE")
            if bool(candidate.get("market_closed", False)):
                risk_reasons.append("MARKET_CLOSED")
            if bool(candidate.get("emergency_stop_engaged", False)):
                risk_reasons.append("EMERGENCY_STOP_ENGAGED")
            risk_approved = not risk_reasons

        phrase_verified = approval_phrase == APPROVAL_PHRASE
        manual_approval_ready = bool(
            policy.get("manual_approval_required", False)
            and phrase_verified
        )

        now = datetime.now(timezone.utc).isoformat()
        candidate_id = ""
        prepared_written = False
        risk_written = False
        approval_written = False
        token_written = False
        duplicate_token = False

        blocking_before_output = sum(
            1 for issue in issues if issue.get("blocking")
        )
        preparation_ready = bool(
            endpoint_verified
            and dashboard_read_only
            and policy_ready
            and candidate_ready
            and account_ready
            and risk_approved
            and blocking_before_output == 0
        )

        if preparation_ready:
            candidate_id = _candidate_id(
                preparation_id,
                symbol,
                side,
                quantity,
                reference_price,
            )

            prepared_payload = {
                "stage": "OP3.01",
                "preparation_id": preparation_id,
                "candidate_id": candidate_id,
                "signal_id": candidate.get("signal_id", ""),
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "time_in_force": time_in_force,
                "quantity": quantity,
                "reference_price": reference_price,
                "estimated_notional": round(notional, 8),
                "endpoint": PAPER_BASE_URL,
                "paper_only": True,
                "order_submission_enabled": False,
                "submission_attempted": False,
                "created_at": now,
            }
            _write(prepared_order_path, prepared_payload)
            prepared_written = True

            _write(risk_report_path, {
                "stage": "OP3.02",
                "preparation_id": preparation_id,
                "candidate_id": candidate_id,
                "risk_approved": risk_approved,
                "risk_reasons": risk_reasons,
                "maximum_order_notional": float(
                    policy["maximum_order_notional"]
                ),
                "maximum_order_quantity": int(
                    policy["maximum_order_quantity"]
                ),
                "estimated_notional": round(notional, 8),
                "created_at": now,
            })
            risk_written = True

            _write(approval_gate_path, {
                "stage": "OP3.03",
                "preparation_id": preparation_id,
                "candidate_id": candidate_id,
                "manual_approval_required": True,
                "approval_phrase_verified": phrase_verified,
                "manual_approval_ready": manual_approval_ready,
                "approved_for_preparation_only": manual_approval_ready,
                "approved_for_submission": False,
                "created_at": now,
            })
            approval_written = True

            token_payload = {
                "stage": "OP3.04",
                "preparation_id": preparation_id,
                "candidate_id": candidate_id,
                "controlled_paper_order_preparation_ready": True,
                "manual_approval_ready": manual_approval_ready,
                "paper_only": True,
                "order_submission_enabled": False,
                "network_write_enabled": False,
                "live_trading_enabled": False,
                "created_at": now,
            }

            if preparation_token_path.exists():
                existing = _load(preparation_token_path)
                if existing.get("candidate_id") == candidate_id:
                    duplicate_token = True
                else:
                    issues.append({
                        "code": "PREPARATION_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "another candidate owns the token",
                    })
            else:
                _write(preparation_token_path, token_payload)
                token_written = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0

        final_ready = bool(
            preparation_ready
            and prepared_written
            and risk_written
            and approval_written
            and (token_written or duplicate_token)
            and not safe_mode
        )

        if safe_mode:
            state, status = (
                "CONTROLLED_PAPER_PREPARATION_SAFE_MODE",
                "BLOCKED",
            )
        elif final_ready:
            state, status = (
                "CONTROLLED_PAPER_ORDER_PREPARATION_READY",
                "PASS",
            )
        else:
            state, status = (
                "WAIT_CONTROLLED_PAPER_INPUT",
                "PASS",
            )

        result = {
            "stage_range": "OP3.01-OP3.04",
            "implementation_type": (
                "CONTROLLED_PAPER_ORDER_PREPARATION"
            ),
            "status": status,
            "state": state,
            "preparation_id": preparation_id,
            "candidate_id": candidate_id,
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "time_in_force": time_in_force,
            "quantity": quantity,
            "reference_price": reference_price,
            "estimated_notional": round(notional, 8),
            "endpoint_verified": endpoint_verified,
            "policy_ready": policy_ready,
            "candidate_ready": candidate_ready,
            "account_ready": account_ready,
            "risk_approved": risk_approved,
            "risk_reasons": risk_reasons,
            "approval_phrase_verified": phrase_verified,
            "manual_approval_ready": manual_approval_ready,
            "prepared_order_written": prepared_written,
            "risk_report_written": risk_written,
            "approval_gate_written": approval_written,
            "preparation_token_written": token_written,
            "duplicate_preparation_token": duplicate_token,
            "controlled_paper_order_preparation_ready": final_ready,
            "paper_only": True,
            "preparation_only": True,
            "order_submission_enabled": False,
            "network_write_enabled": False,
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
                "OP3_05_SINGLE_PAPER_ORDER_EXECUTION"
                if final_ready and manual_approval_ready
                else "OP3_01_TO_OP3_04_WAIT_APPROVAL_OR_INPUT"
            ),
            "validation_mode": (
                "LOCAL_CONTROLLED_PAPER_PREPARATION_ONLY"
            ),
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
