from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"
SUBMISSION_APPROVAL_PHRASE = (
    "APPROVE OP3 SINGLE CONTROLLED PAPER ORDER"
)


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


def _default_transport(
    *,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout_seconds: int,
) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            **headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return int(response.status), payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"message": raw}
        return int(exc.code), payload


class SingleControlledPaperOrderExecution:
    def run(
        self,
        *,
        preparation_result_path: Path,
        prepared_order_path: Path,
        execution_policy_path: Path,
        submission_receipt_path: Path,
        execution_ledger_path: Path,
        execution_token_path: Path,
        result_path: Path,
        enable_network: bool = False,
        enable_submission: bool = False,
        approval_phrase: str = "",
        base_url: str = PAPER_BASE_URL,
        transport: Callable[..., tuple[int, dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        preparation = {}
        prepared_order = {}
        policy = {}

        for name, path in (
            ("PREPARATION_RESULT", preparation_result_path),
            ("PREPARED_ORDER", prepared_order_path),
            ("EXECUTION_POLICY", execution_policy_path),
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
            if name == "PREPARATION_RESULT":
                preparation = loaded
            elif name == "PREPARED_ORDER":
                prepared_order = loaded
            else:
                policy = loaded

        preparation_ready = bool(
            preparation.get(
                "controlled_paper_order_preparation_ready",
                False,
            )
        )
        manual_preparation_approved = bool(
            preparation.get("manual_approval_ready", False)
        )
        preparation_safe = bool(
            preparation.get("safe_mode_engaged", False)
        )

        if preparation and not preparation_ready:
            issues.append({
                "code": "PREPARATION_NOT_READY",
                "blocking": True,
                "detail": str(preparation.get("state", "")),
            })
        if preparation_safe:
            issues.append({
                "code": "PREPARATION_SAFE_MODE",
                "blocking": True,
                "detail": "preparation safe mode is engaged",
            })
        if preparation and not manual_preparation_approved:
            issues.append({
                "code": "PREPARATION_MANUAL_APPROVAL_MISSING",
                "blocking": True,
                "detail": "OP3.01-OP3.04 approval is required",
            })

        endpoint_verified = (
            base_url.rstrip("/") == PAPER_BASE_URL
        )
        if not endpoint_verified:
            issues.append({
                "code": "LIVE_OR_UNKNOWN_ENDPOINT_BLOCKED",
                "blocking": True,
                "detail": base_url,
            })

        policy_ready = False
        execution_id = ""
        if policy:
            execution_id = str(
                policy.get("execution_id", "")
            ).strip()
            checks = [
                ("EXECUTION_ID_MISSING", bool(execution_id)),
                (
                    "PAPER_ONLY_REQUIRED",
                    bool(policy.get("paper_only", False)),
                ),
                (
                    "SINGLE_ORDER_ONLY_REQUIRED",
                    int(policy.get("maximum_orders_per_run", 0))
                    == 1,
                ),
                (
                    "MAX_NOTIONAL_INVALID",
                    0
                    < float(policy.get("maximum_order_notional", 0))
                    <= 100,
                ),
                (
                    "MAX_QUANTITY_INVALID",
                    1
                    <= int(policy.get("maximum_order_quantity", 0))
                    <= 5,
                ),
                (
                    "MARKET_ORDER_ONLY_REQUIRED",
                    bool(policy.get("market_order_only", False)),
                ),
                (
                    "DAY_TIME_IN_FORCE_ONLY_REQUIRED",
                    bool(policy.get("day_time_in_force_only", False)),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(
                        policy.get("live_trading_enabled", True)
                    ),
                ),
                (
                    "EXACT_ENDPOINT_REQUIRED",
                    str(
                        policy.get("expected_base_url", "")
                    ).rstrip("/")
                    == PAPER_BASE_URL,
                ),
                (
                    "TIMEOUT_INVALID",
                    3
                    <= int(policy.get("timeout_seconds", 0))
                    <= 30,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "execution policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        candidate_ready = False
        candidate_id = ""
        symbol = ""
        side = ""
        quantity = 0
        order_type = ""
        time_in_force = ""
        reference_price = 0.0
        estimated_notional = 0.0
        client_order_id = ""

        if prepared_order:
            candidate_id = str(
                prepared_order.get("candidate_id", "")
            ).strip()
            symbol = str(
                prepared_order.get("symbol", "")
            ).upper().strip()
            side = str(
                prepared_order.get("side", "")
            ).lower().strip()
            quantity = int(prepared_order.get("quantity", 0))
            order_type = str(
                prepared_order.get("order_type", "")
            ).lower().strip()
            time_in_force = str(
                prepared_order.get("time_in_force", "")
            ).lower().strip()
            reference_price = float(
                prepared_order.get("reference_price", 0)
            )
            estimated_notional = float(
                prepared_order.get(
                    "estimated_notional",
                    quantity * reference_price,
                )
            )
            client_order_id = (
                "op3-" + candidate_id[-24:]
                if candidate_id
                else ""
            )

            checks = [
                ("CANDIDATE_ID_MISSING", bool(candidate_id)),
                ("SYMBOL_MISSING", bool(symbol)),
                ("SIDE_INVALID", side in {"buy", "sell"}),
                ("QUANTITY_INVALID", quantity > 0),
                ("ORDER_TYPE_NOT_MARKET", order_type == "market"),
                (
                    "TIME_IN_FORCE_NOT_DAY",
                    time_in_force == "day",
                ),
                (
                    "PREPARED_ORDER_NOT_PAPER_ONLY",
                    bool(prepared_order.get("paper_only", False)),
                ),
                (
                    "PREPARED_ORDER_ALREADY_SUBMITTED",
                    not bool(
                        prepared_order.get(
                            "submission_attempted",
                            True,
                        )
                    ),
                ),
                (
                    "PREPARED_ENDPOINT_INVALID",
                    str(
                        prepared_order.get("endpoint", "")
                    ).rstrip("/")
                    == PAPER_BASE_URL,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "prepared order gate failed",
                    })
            candidate_ready = all(passed for _, passed in checks)

        limits_ready = False
        if policy_ready and candidate_ready:
            limit_reasons = []
            if quantity > int(policy["maximum_order_quantity"]):
                limit_reasons.append("QUANTITY_LIMIT_EXCEEDED")
            if estimated_notional > float(
                policy["maximum_order_notional"]
            ):
                limit_reasons.append("NOTIONAL_LIMIT_EXCEEDED")
            for reason in limit_reasons:
                issues.append({
                    "code": reason,
                    "blocking": True,
                    "detail": str(estimated_notional),
                })
            limits_ready = not limit_reasons

        duplicate_submission = False
        if execution_ledger_path.exists() and client_order_id:
            for line in execution_ledger_path.read_text(
                encoding="utf-8"
            ).splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                if (
                    isinstance(item, dict)
                    and item.get("client_order_id")
                    == client_order_id
                ):
                    duplicate_submission = True
                    break
        if duplicate_submission:
            issues.append({
                "code": "DUPLICATE_SUBMISSION_BLOCKED",
                "blocking": True,
                "detail": client_order_id,
            })

        credentials_configured = bool(
            os.getenv("APCA_API_KEY_ID", "").strip()
            and os.getenv(
                "APCA_API_SECRET_KEY",
                "",
            ).strip()
        )
        approval_verified = (
            approval_phrase == SUBMISSION_APPROVAL_PHRASE
        )

        submission_requested = bool(
            enable_network and enable_submission
        )
        submission_gate_ready = bool(
            submission_requested
            and approval_verified
            and credentials_configured
            and endpoint_verified
            and preparation_ready
            and manual_preparation_approved
            and policy_ready
            and candidate_ready
            and limits_ready
            and not duplicate_submission
            and not any(i.get("blocking") for i in issues)
        )

        now = datetime.now(timezone.utc).isoformat()
        preview = {
            "execution_id": execution_id,
            "candidate_id": candidate_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "qty": quantity,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
        }

        network_requests = 0
        write_requests = 0
        paper_orders_submitted = 0
        response_status = 0
        response_payload: dict[str, Any] = {}
        broker_order_id = ""
        broker_order_status = ""
        submission_succeeded = False
        receipt_written = False
        ledger_written = False
        token_written = False

        if submission_gate_ready:
            request_transport = transport or _default_transport
            headers = {
                "APCA-API-KEY-ID": os.environ[
                    "APCA_API_KEY_ID"
                ].strip(),
                "APCA-API-SECRET-KEY": os.environ[
                    "APCA_API_SECRET_KEY"
                ].strip(),
            }
            network_requests = 1
            write_requests = 1
            response_status, response_payload = request_transport(
                url=PAPER_BASE_URL + "/v2/orders",
                headers=headers,
                body={
                    "symbol": symbol,
                    "qty": str(quantity),
                    "side": side,
                    "type": order_type,
                    "time_in_force": time_in_force,
                    "client_order_id": client_order_id,
                },
                timeout_seconds=int(policy["timeout_seconds"]),
            )
            submission_succeeded = (
                200 <= response_status < 300
                and bool(str(response_payload.get("id", "")).strip())
            )
            if submission_succeeded:
                paper_orders_submitted = 1
                broker_order_id = str(
                    response_payload.get("id", "")
                )
                broker_order_status = str(
                    response_payload.get("status", "")
                )
            else:
                issues.append({
                    "code": "PAPER_ORDER_SUBMISSION_FAILED",
                    "blocking": True,
                    "detail": (
                        f"HTTP {response_status}: "
                        f"{response_payload.get('message', '')}"
                    ),
                })

            _write(submission_receipt_path, {
                "stage": "OP3.06",
                "execution_id": execution_id,
                "candidate_id": candidate_id,
                "client_order_id": client_order_id,
                "http_status": response_status,
                "submission_succeeded": submission_succeeded,
                "broker_order_id": broker_order_id,
                "broker_order_status": broker_order_status,
                "response": response_payload,
                "paper_only": True,
                "created_at": now,
            })
            receipt_written = True

            if submission_succeeded:
                execution_ledger_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                with execution_ledger_path.open(
                    "a",
                    encoding="utf-8",
                    newline="\n",
                ) as stream:
                    stream.write(json.dumps({
                        "stage": "OP3.07",
                        "execution_id": execution_id,
                        "candidate_id": candidate_id,
                        "client_order_id": client_order_id,
                        "broker_order_id": broker_order_id,
                        "broker_order_status": broker_order_status,
                        "symbol": symbol,
                        "side": side,
                        "quantity": quantity,
                        "paper_only": True,
                        "submitted_at": now,
                    }, sort_keys=True) + "\n")
                ledger_written = True

                _write(execution_token_path, {
                    "stage": "OP3.08",
                    "execution_id": execution_id,
                    "candidate_id": candidate_id,
                    "client_order_id": client_order_id,
                    "broker_order_id": broker_order_id,
                    "single_controlled_paper_order_executed": True,
                    "paper_orders_submitted": 1,
                    "live_orders_submitted": 0,
                    "created_at": now,
                })
                token_written = True

        blocking = sum(
            1 for issue in issues if issue.get("blocking")
        )
        safe_mode = blocking > 0

        if safe_mode:
            state, status = (
                "SINGLE_PAPER_ORDER_EXECUTION_SAFE_MODE",
                "BLOCKED",
            )
        elif submission_succeeded:
            state, status = (
                "SINGLE_CONTROLLED_PAPER_ORDER_SUBMITTED",
                "PASS",
            )
        elif (
            preparation_ready
            and manual_preparation_approved
            and policy_ready
            and candidate_ready
            and limits_ready
        ):
            state, status = (
                "SINGLE_PAPER_ORDER_EXECUTION_ARMED",
                "PASS",
            )
        else:
            state, status = (
                "WAIT_CONTROLLED_PAPER_PREPARATION",
                "PASS",
            )

        result = {
            "stage_range": "OP3.05-OP3.08",
            "implementation_type": (
                "SINGLE_CONTROLLED_PAPER_ORDER_EXECUTION"
            ),
            "status": status,
            "state": state,
            "execution_id": execution_id,
            "candidate_id": candidate_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "estimated_notional": estimated_notional,
            "endpoint_verified": endpoint_verified,
            "preparation_ready": preparation_ready,
            "manual_preparation_approved": (
                manual_preparation_approved
            ),
            "policy_ready": policy_ready,
            "candidate_ready": candidate_ready,
            "limits_ready": limits_ready,
            "duplicate_submission": duplicate_submission,
            "credentials_configured": credentials_configured,
            "approval_phrase_verified": approval_verified,
            "enable_network": enable_network,
            "enable_submission": enable_submission,
            "submission_requested": submission_requested,
            "submission_gate_ready": submission_gate_ready,
            "order_preview": preview,
            "response_http_status": response_status,
            "broker_order_id": broker_order_id,
            "broker_order_status": broker_order_status,
            "submission_succeeded": submission_succeeded,
            "submission_receipt_written": receipt_written,
            "execution_ledger_written": ledger_written,
            "execution_token_written": token_written,
            "paper_only": True,
            "live_trading_enabled": False,
            "actual_credentials_used": submission_gate_ready,
            "actual_external_network_used": (
                network_requests > 0
            ),
            "network_requests_executed": network_requests,
            "write_requests_executed": write_requests,
            "actual_paper_orders_submitted": (
                paper_orders_submitted
            ),
            "live_orders_submitted": 0,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "OP3_09_PAPER_ORDER_LIFECYCLE"
                if submission_succeeded
                else "OP3_05_TO_OP3_08_WAIT_EXPLICIT_SUBMISSION"
            ),
            "validation_mode": (
                "ACTUAL_ALPACA_PAPER_SINGLE_ORDER"
                if submission_requested
                else "LOCAL_SINGLE_ORDER_PREVIEW_ONLY"
            ),
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
