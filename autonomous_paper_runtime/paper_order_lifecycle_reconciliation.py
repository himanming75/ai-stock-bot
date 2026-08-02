from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"

TERMINAL_STATUSES = {
    "filled", "canceled", "expired", "rejected",
}
OPEN_STATUSES = {
    "new", "accepted", "pending_new", "partially_filled",
    "accepted_for_bidding", "stopped", "pending_cancel",
    "pending_replace", "calculated", "held",
}


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
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


def _default_get(
    *,
    url: str,
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[int, Any]:
    request = urllib.request.Request(
        url=url,
        headers={
            **headers,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=timeout_seconds
        ) as response:
            raw = response.read().decode("utf-8")
            return int(response.status), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"message": raw}
        return int(exc.code), payload


class PaperOrderLifecycleReconciliation:
    def run(
        self,
        *,
        execution_result_path: Path,
        submission_receipt_path: Path,
        lifecycle_policy_path: Path,
        local_order_snapshot_path: Path,
        local_positions_snapshot_path: Path,
        local_account_snapshot_path: Path,
        order_status_path: Path,
        fill_report_path: Path,
        reconciliation_report_path: Path,
        recovery_token_path: Path,
        audit_ledger_path: Path,
        result_path: Path,
        enable_network: bool = False,
        base_url: str = PAPER_BASE_URL,
        transport: Callable[..., tuple[int, Any]] | None = None,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        execution = {}
        receipt = {}
        policy = {}

        for name, path in (
            ("EXECUTION_RESULT", execution_result_path),
            ("SUBMISSION_RECEIPT", submission_receipt_path),
            ("LIFECYCLE_POLICY", lifecycle_policy_path),
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
            if name == "EXECUTION_RESULT":
                execution = loaded
            elif name == "SUBMISSION_RECEIPT":
                receipt = loaded
            else:
                policy = loaded

        submitted = bool(
            execution.get("submission_succeeded", False)
            and int(
                execution.get("actual_paper_orders_submitted", 0)
            ) == 1
        )
        if execution and not submitted:
            issues.append({
                "code": "PAPER_ORDER_NOT_SUBMITTED",
                "blocking": True,
                "detail": str(execution.get("state", "")),
            })
        if execution.get("safe_mode_engaged"):
            issues.append({
                "code": "EXECUTION_SAFE_MODE",
                "blocking": True,
                "detail": "prior stage safe mode",
            })

        endpoint_verified = base_url.rstrip("/") == PAPER_BASE_URL
        if not endpoint_verified:
            issues.append({
                "code": "LIVE_OR_UNKNOWN_ENDPOINT_BLOCKED",
                "blocking": True,
                "detail": base_url,
            })

        lifecycle_id = ""
        policy_ready = False
        if policy:
            lifecycle_id = str(
                policy.get("lifecycle_id", "")
            ).strip()
            checks = [
                ("LIFECYCLE_ID_MISSING", bool(lifecycle_id)),
                (
                    "PAPER_ONLY_REQUIRED",
                    bool(policy.get("paper_only", False)),
                ),
                (
                    "READ_ONLY_REQUIRED",
                    bool(policy.get("read_only", False)),
                ),
                (
                    "ORDER_WRITE_MUST_BE_DISABLED",
                    not bool(policy.get("order_write_enabled", True)),
                ),
                (
                    "CANCEL_MUST_BE_DISABLED",
                    not bool(policy.get("cancel_enabled", True)),
                ),
                (
                    "REPLACE_MUST_BE_DISABLED",
                    not bool(policy.get("replace_enabled", True)),
                ),
                (
                    "TIMEOUT_INVALID",
                    3 <= int(policy.get("timeout_seconds", 0)) <= 30,
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
                        "detail": "lifecycle policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        broker_order_id = str(
            execution.get(
                "broker_order_id",
                receipt.get("broker_order_id", ""),
            )
        ).strip()
        client_order_id = str(
            execution.get(
                "client_order_id",
                receipt.get("client_order_id", ""),
            )
        ).strip()
        symbol = str(
            execution.get("symbol", "")
        ).upper().strip()
        expected_side = str(
            execution.get("side", "")
        ).lower().strip()
        expected_qty = float(execution.get("quantity", 0) or 0)

        if not broker_order_id:
            issues.append({
                "code": "BROKER_ORDER_ID_MISSING",
                "blocking": True,
                "detail": "",
            })

        credentials_configured = bool(
            os.getenv("APCA_API_KEY_ID", "").strip()
            and os.getenv("APCA_API_SECRET_KEY", "").strip()
        )

        network_requests = 0
        order_http_status = positions_http_status = account_http_status = 0
        order_snapshot: dict[str, Any] = {}
        positions_snapshot: list[dict[str, Any]] = []
        account_snapshot: dict[str, Any] = {}

        if (
            enable_network
            and endpoint_verified
            and credentials_configured
            and broker_order_id
            and not any(i.get("blocking") for i in issues)
        ):
            getter = transport or _default_get
            headers = {
                "APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"].strip(),
                "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"].strip(),
            }
            timeout = int(policy["timeout_seconds"])

            order_http_status, order_payload = getter(
                url=f"{PAPER_BASE_URL}/v2/orders/{urllib.parse.quote(broker_order_id)}",
                headers=headers,
                timeout_seconds=timeout,
            )
            network_requests += 1
            if isinstance(order_payload, dict):
                order_snapshot = order_payload

            positions_http_status, positions_payload = getter(
                url=f"{PAPER_BASE_URL}/v2/positions",
                headers=headers,
                timeout_seconds=timeout,
            )
            network_requests += 1
            if isinstance(positions_payload, list):
                positions_snapshot = [
                    item for item in positions_payload
                    if isinstance(item, dict)
                ]

            account_http_status, account_payload = getter(
                url=f"{PAPER_BASE_URL}/v2/account",
                headers=headers,
                timeout_seconds=timeout,
            )
            network_requests += 1
            if isinstance(account_payload, dict):
                account_snapshot = account_payload

            for name, status in (
                ("ORDER", order_http_status),
                ("POSITIONS", positions_http_status),
                ("ACCOUNT", account_http_status),
            ):
                if not 200 <= status < 300:
                    issues.append({
                        "code": f"{name}_READ_FAILED",
                        "blocking": True,
                        "detail": str(status),
                    })
        else:
            try:
                order_snapshot = _load(local_order_snapshot_path)
            except Exception as exc:
                issues.append({
                    "code": "INVALID_LOCAL_ORDER_SNAPSHOT",
                    "blocking": True,
                    "detail": str(exc),
                })

            positions_payload = {}
            try:
                positions_payload = _load(local_positions_snapshot_path)
            except Exception as exc:
                issues.append({
                    "code": "INVALID_LOCAL_POSITIONS_SNAPSHOT",
                    "blocking": True,
                    "detail": str(exc),
                })
            raw_positions = positions_payload.get("positions", [])
            if isinstance(raw_positions, list):
                positions_snapshot = [
                    item for item in raw_positions
                    if isinstance(item, dict)
                ]

            try:
                account_snapshot = _load(local_account_snapshot_path)
            except Exception as exc:
                issues.append({
                    "code": "INVALID_LOCAL_ACCOUNT_SNAPSHOT",
                    "blocking": True,
                    "detail": str(exc),
                })

        if not order_snapshot:
            issues.append({
                "code": "ORDER_SNAPSHOT_NOT_AVAILABLE",
                "blocking": True,
                "detail": str(local_order_snapshot_path),
            })
        if not account_snapshot:
            issues.append({
                "code": "ACCOUNT_SNAPSHOT_NOT_AVAILABLE",
                "blocking": True,
                "detail": str(local_account_snapshot_path),
            })

        order_status = str(
            order_snapshot.get("status", "")
        ).lower().strip()
        filled_qty = float(
            order_snapshot.get("filled_qty", 0) or 0
        )
        filled_avg_price = float(
            order_snapshot.get("filled_avg_price", 0) or 0
        )
        order_symbol = str(
            order_snapshot.get("symbol", "")
        ).upper().strip()
        order_side = str(
            order_snapshot.get("side", "")
        ).lower().strip()
        order_qty = float(
            order_snapshot.get("qty", 0) or 0
        )

        order_identity_verified = bool(
            order_snapshot
            and str(order_snapshot.get("id", "")).strip()
            == broker_order_id
            and (
                not client_order_id
                or str(
                    order_snapshot.get("client_order_id", "")
                ).strip() == client_order_id
            )
            and order_symbol == symbol
            and order_side == expected_side
            and order_qty == expected_qty
        )
        if order_snapshot and not order_identity_verified:
            issues.append({
                "code": "ORDER_IDENTITY_MISMATCH",
                "blocking": True,
                "detail": order_symbol,
            })

        known_status = (
            order_status in TERMINAL_STATUSES
            or order_status in OPEN_STATUSES
        )
        if order_snapshot and not known_status:
            issues.append({
                "code": "UNKNOWN_ORDER_STATUS",
                "blocking": True,
                "detail": order_status,
            })

        fill_state = (
            "FILLED"
            if order_status == "filled"
            else "PARTIALLY_FILLED"
            if filled_qty > 0
            else "NOT_FILLED"
        )

        matching_position = next(
            (
                item for item in positions_snapshot
                if str(item.get("symbol", "")).upper().strip()
                == symbol
            ),
            {},
        )
        position_qty = float(
            matching_position.get("qty", 0) or 0
        )

        expected_position_qty = (
            filled_qty if expected_side == "buy"
            else -filled_qty
        )
        position_required = filled_qty > 0
        position_reconciled = (
            not position_required
            or position_qty == expected_position_qty
        )

        account_status = str(
            account_snapshot.get(
                "status",
                account_snapshot.get("account", {}).get("status", "")
                if isinstance(account_snapshot.get("account"), dict)
                else "",
            )
        ).upper()
        account_blocked = bool(
            account_snapshot.get(
                "account_blocked",
                account_snapshot.get("account", {}).get(
                    "account_blocked", False
                )
                if isinstance(account_snapshot.get("account"), dict)
                else False,
            )
        )
        trading_blocked = bool(
            account_snapshot.get(
                "trading_blocked",
                account_snapshot.get("account", {}).get(
                    "trading_blocked", False
                )
                if isinstance(account_snapshot.get("account"), dict)
                else False,
            )
        )
        account_reconciled = bool(
            account_status == "ACTIVE"
            and not account_blocked
            and not trading_blocked
        )

        if order_snapshot and position_required and not position_reconciled:
            issues.append({
                "code": "POSITION_RECONCILIATION_MISMATCH",
                "blocking": True,
                "detail": (
                    f"expected={expected_position_qty},"
                    f"actual={position_qty}"
                ),
            })
        if account_snapshot and not account_reconciled:
            issues.append({
                "code": "ACCOUNT_RECONCILIATION_FAILED",
                "blocking": True,
                "detail": account_status,
            })

        lifecycle_complete = bool(
            order_status in TERMINAL_STATUSES
        )
        recovery_required = bool(
            order_status in OPEN_STATUSES
        )

        now = datetime.now(timezone.utc).isoformat()
        status_written = fill_written = reconciliation_written = False
        recovery_written = ledger_written = False

        blocking_before_write = sum(
            1 for issue in issues if issue.get("blocking")
        )
        lifecycle_ready = bool(
            submitted
            and policy_ready
            and endpoint_verified
            and order_identity_verified
            and known_status
            and account_reconciled
            and position_reconciled
            and blocking_before_write == 0
        )

        if lifecycle_ready:
            _write(order_status_path, {
                "stage": "OP3.09",
                "lifecycle_id": lifecycle_id,
                "broker_order_id": broker_order_id,
                "client_order_id": client_order_id,
                "symbol": symbol,
                "status": order_status,
                "terminal": lifecycle_complete,
                "recovery_required": recovery_required,
                "observed_at": now,
            })
            status_written = True

            _write(fill_report_path, {
                "stage": "OP3.10",
                "lifecycle_id": lifecycle_id,
                "broker_order_id": broker_order_id,
                "fill_state": fill_state,
                "filled_qty": filled_qty,
                "filled_avg_price": filled_avg_price,
                "expected_qty": expected_qty,
                "fully_filled": (
                    order_status == "filled"
                    and filled_qty == expected_qty
                ),
                "observed_at": now,
            })
            fill_written = True

            _write(reconciliation_report_path, {
                "stage": "OP3.11",
                "lifecycle_id": lifecycle_id,
                "symbol": symbol,
                "expected_position_qty": expected_position_qty,
                "actual_position_qty": position_qty,
                "position_reconciled": position_reconciled,
                "account_status": account_status,
                "account_reconciled": account_reconciled,
                "reconciliation_ready": True,
                "observed_at": now,
            })
            reconciliation_written = True

            _write(recovery_token_path, {
                "stage": "OP3.12",
                "lifecycle_id": lifecycle_id,
                "broker_order_id": broker_order_id,
                "client_order_id": client_order_id,
                "order_status": order_status,
                "recovery_required": recovery_required,
                "resume_action": (
                    "READ_ORDER_AND_RECONCILE"
                    if recovery_required
                    else "NO_RECOVERY_REQUIRED"
                ),
                "paper_order_lifecycle_ready": True,
                "created_at": now,
            })
            recovery_written = True

            _append_jsonl(audit_ledger_path, {
                "stage_range": "OP3.09-OP3.12",
                "lifecycle_id": lifecycle_id,
                "broker_order_id": broker_order_id,
                "client_order_id": client_order_id,
                "symbol": symbol,
                "side": expected_side,
                "order_status": order_status,
                "filled_qty": filled_qty,
                "filled_avg_price": filled_avg_price,
                "position_qty": position_qty,
                "position_reconciled": position_reconciled,
                "account_reconciled": account_reconciled,
                "recovery_required": recovery_required,
                "paper_only": True,
                "observed_at": now,
            })
            ledger_written = True

        blocking = sum(
            1 for issue in issues if issue.get("blocking")
        )
        safe_mode = blocking > 0

        if safe_mode:
            state, status = (
                "PAPER_ORDER_LIFECYCLE_SAFE_MODE",
                "BLOCKED",
            )
        elif lifecycle_ready:
            state, status = (
                "PAPER_ORDER_LIFECYCLE_COMPLETE"
                if lifecycle_complete
                else "PAPER_ORDER_LIFECYCLE_MONITORING",
                "PASS",
            )
        else:
            state, status = (
                "WAIT_PAPER_ORDER_EXECUTION",
                "PASS",
            )

        result = {
            "stage_range": "OP3.09-OP3.12",
            "implementation_type": (
                "PAPER_ORDER_LIFECYCLE_RECONCILIATION"
            ),
            "status": status,
            "state": state,
            "lifecycle_id": lifecycle_id,
            "broker_order_id": broker_order_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": expected_side,
            "expected_qty": expected_qty,
            "order_status": order_status,
            "fill_state": fill_state,
            "filled_qty": filled_qty,
            "filled_avg_price": filled_avg_price,
            "position_qty": position_qty,
            "position_reconciled": position_reconciled,
            "account_status": account_status,
            "account_reconciled": account_reconciled,
            "lifecycle_complete": lifecycle_complete,
            "recovery_required": recovery_required,
            "endpoint_verified": endpoint_verified,
            "credentials_configured": credentials_configured,
            "enable_network": enable_network,
            "order_http_status": order_http_status,
            "positions_http_status": positions_http_status,
            "account_http_status": account_http_status,
            "order_status_written": status_written,
            "fill_report_written": fill_written,
            "reconciliation_report_written": reconciliation_written,
            "recovery_token_written": recovery_written,
            "audit_ledger_written": ledger_written,
            "paper_order_lifecycle_ready": lifecycle_ready,
            "paper_only": True,
            "read_only": True,
            "order_write_enabled": False,
            "cancel_enabled": False,
            "replace_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": bool(
                enable_network and credentials_configured
            ),
            "actual_external_network_used": (
                network_requests > 0
            ),
            "network_requests_executed": network_requests,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "OP3_13_LIMITED_AUTONOMOUS_PAPER_TRADING"
                if lifecycle_complete
                else "OP3_09_TO_OP3_12_CONTINUE_MONITORING"
            ),
            "validation_mode": (
                "ACTUAL_ALPACA_PAPER_READ_ONLY"
                if enable_network
                else "LOCAL_PAPER_LIFECYCLE_SNAPSHOT_ONLY"
            ),
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
