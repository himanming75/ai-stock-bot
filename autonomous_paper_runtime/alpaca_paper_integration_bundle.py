from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"
APPROVAL_PHRASE = "APPROVE V140 PAPER ORDER SUBMISSION"


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


def _request_json(
    *,
    method: str,
    url: str,
    api_key: str,
    api_secret: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 15,
) -> dict[str, Any] | list[Any]:
    body = None
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=url,
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8")
        if not raw:
            return {}
        return json.loads(raw)


def _paper_endpoint_verified(base_url: str) -> bool:
    return base_url.rstrip("/") == PAPER_BASE_URL


class AlpacaPaperIntegrationBundle:
    def run(
        self,
        *,
        engine_result_path: Path,
        engine_token_path: Path,
        order_candidate_path: Path,
        local_broker_snapshot_path: Path,
        reconciliation_snapshot_path: Path,
        read_result_path: Path,
        submission_result_path: Path,
        reconciliation_result_path: Path,
        final_result_path: Path,
        base_url: str = PAPER_BASE_URL,
        enable_network: bool = False,
        enable_submission: bool = False,
        approval_phrase: str = "",
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        network_requests = 0
        write_requests = 0
        paper_orders_submitted = 0
        credentials_used = False

        try:
            engine = _load_json(engine_result_path)
        except Exception as exc:
            engine = {}
            issues.append({
                "code": "INVALID_ENGINE_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not engine:
            issues.append({
                "code": "ENGINE_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(engine_result_path),
            })

        source_status = str(engine.get("status", "")).upper()
        source_state = str(engine.get("state", "")).upper()
        source_safe_mode = bool(engine.get("safe_mode_engaged", False))
        engine_ready = bool(engine.get("autonomous_engine_ready", False))
        engine_id = str(engine.get("engine_id", "")).strip()
        runtime_cycle_id = str(engine.get("runtime_cycle_id", "")).strip()

        if source_status == "BLOCKED" or source_safe_mode:
            issues.append({
                "code": "SOURCE_ENGINE_SAFE_MODE",
                "blocking": True,
                "detail": source_state,
            })

        integration_required = engine_ready or source_state == "AUTONOMOUS_ENGINE_READY"
        engine_token: dict[str, Any] = {}
        candidate: dict[str, Any] = {}

        if integration_required:
            for code, path in (
                ("ENGINE_TOKEN", engine_token_path),
                ("ORDER_CANDIDATE", order_candidate_path),
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
                if code == "ENGINE_TOKEN":
                    engine_token = loaded
                else:
                    candidate = loaded

        if engine_token and (
            engine_token.get("engine_id") != engine_id
            or engine_token.get("runtime_cycle_id") != runtime_cycle_id
            or not bool(engine_token.get("autonomous_engine_ready", False))
        ):
            issues.append({
                "code": "ENGINE_TOKEN_MISMATCH",
                "blocking": True,
                "detail": "engine result and token do not match",
            })

        endpoint_verified = _paper_endpoint_verified(base_url)
        if integration_required and not endpoint_verified:
            issues.append({
                "code": "NON_PAPER_ENDPOINT_BLOCKED",
                "blocking": True,
                "detail": base_url,
            })

        api_key = os.getenv("APCA_API_KEY_ID", "")
        api_secret = os.getenv("APCA_API_SECRET_KEY", "")
        credentials_present = bool(api_key and api_secret)

        account: dict[str, Any] = {}
        clock: dict[str, Any] = {}
        orders: list[Any] = []
        positions: list[Any] = []
        broker_read_verified = False

        if integration_required and endpoint_verified:
            if enable_network:
                if not credentials_present:
                    issues.append({
                        "code": "PAPER_CREDENTIALS_MISSING",
                        "blocking": True,
                        "detail": "APCA_API_KEY_ID and APCA_API_SECRET_KEY are required",
                    })
                else:
                    credentials_used = True
                    try:
                        account = dict(_request_json(
                            method="GET",
                            url=f"{PAPER_BASE_URL}/v2/account",
                            api_key=api_key,
                            api_secret=api_secret,
                        ))
                        network_requests += 1
                        clock = dict(_request_json(
                            method="GET",
                            url=f"{PAPER_BASE_URL}/v2/clock",
                            api_key=api_key,
                            api_secret=api_secret,
                        ))
                        network_requests += 1
                        orders_payload = _request_json(
                            method="GET",
                            url=f"{PAPER_BASE_URL}/v2/orders?status=open",
                            api_key=api_key,
                            api_secret=api_secret,
                        )
                        network_requests += 1
                        positions_payload = _request_json(
                            method="GET",
                            url=f"{PAPER_BASE_URL}/v2/positions",
                            api_key=api_key,
                            api_secret=api_secret,
                        )
                        network_requests += 1
                        orders = list(orders_payload) if isinstance(orders_payload, list) else []
                        positions = list(positions_payload) if isinstance(positions_payload, list) else []
                    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TypeError) as exc:
                        issues.append({
                            "code": "PAPER_READ_FAILED",
                            "blocking": True,
                            "detail": str(exc),
                        })
            else:
                try:
                    local_snapshot = _load_json(local_broker_snapshot_path)
                except Exception as exc:
                    local_snapshot = {}
                    issues.append({
                        "code": "INVALID_LOCAL_BROKER_SNAPSHOT",
                        "blocking": True,
                        "detail": str(exc),
                    })
                if not local_snapshot:
                    issues.append({
                        "code": "LOCAL_BROKER_SNAPSHOT_NOT_FOUND",
                        "blocking": True,
                        "detail": str(local_broker_snapshot_path),
                    })
                else:
                    account = dict(local_snapshot.get("account", {}))
                    clock = dict(local_snapshot.get("clock", {}))
                    orders = list(local_snapshot.get("open_orders", []))
                    positions = list(local_snapshot.get("positions", []))

        if account or clock:
            checks = [
                ("ACCOUNT_INACTIVE", str(account.get("status", "")).upper() == "ACTIVE"),
                ("TRADING_BLOCKED", not bool(account.get("trading_blocked", False))),
                ("MARKET_CLOSED", bool(clock.get("is_open", False))),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "paper broker read gate failed",
                    })
            broker_read_verified = all(passed for _, passed in checks)

        read_payload = {
            "stage": "V140.10",
            "paper_endpoint_verified": endpoint_verified,
            "broker_read_verified": broker_read_verified,
            "account_status": account.get("status", ""),
            "market_is_open": bool(clock.get("is_open", False)),
            "open_order_count": len(orders),
            "position_count": len(positions),
            "network_enabled": enable_network,
            "network_requests_executed": network_requests,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(read_result_path, read_payload)

        submission_allowed = bool(
            integration_required
            and endpoint_verified
            and broker_read_verified
            and candidate
            and not orders
            and approval_phrase == APPROVAL_PHRASE
            and enable_network
            and enable_submission
            and credentials_present
            and not any(issue.get("blocking") for issue in issues)
        )

        client_order_id = str(candidate.get("engine_id", engine_id)).strip()
        existing_order: dict[str, Any] = {}
        submitted_order: dict[str, Any] = {}
        duplicate_order = False

        if submission_allowed:
            lookup_url = (
                f"{PAPER_BASE_URL}/v2/orders:by_client_order_id?"
                + urllib.parse.urlencode({"client_order_id": client_order_id})
            )
            try:
                existing_payload = _request_json(
                    method="GET",
                    url=lookup_url,
                    api_key=api_key,
                    api_secret=api_secret,
                )
                network_requests += 1
                existing_order = dict(existing_payload) if isinstance(existing_payload, dict) else {}
                duplicate_order = bool(existing_order)
            except urllib.error.HTTPError as exc:
                network_requests += 1
                if exc.code != 404:
                    issues.append({
                        "code": "IDEMPOTENCY_LOOKUP_FAILED",
                        "blocking": True,
                        "detail": str(exc),
                    })
            except (urllib.error.URLError, ValueError, TypeError) as exc:
                network_requests += 1
                issues.append({
                    "code": "IDEMPOTENCY_LOOKUP_FAILED",
                    "blocking": True,
                    "detail": str(exc),
                })

            if not duplicate_order and not any(issue.get("blocking") for issue in issues):
                order_payload = {
                    "symbol": str(candidate.get("symbol", "")).upper(),
                    "qty": str(candidate.get("quantity", "")),
                    "side": str(candidate.get("side", "")).lower(),
                    "type": str(candidate.get("order_type", "MARKET")).lower(),
                    "time_in_force": str(candidate.get("time_in_force", "DAY")).lower(),
                    "client_order_id": client_order_id,
                }
                try:
                    response = _request_json(
                        method="POST",
                        url=f"{PAPER_BASE_URL}/v2/orders",
                        api_key=api_key,
                        api_secret=api_secret,
                        payload=order_payload,
                    )
                    network_requests += 1
                    write_requests += 1
                    paper_orders_submitted += 1
                    submitted_order = dict(response) if isinstance(response, dict) else {}
                except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TypeError) as exc:
                    network_requests += 1
                    write_requests += 1
                    issues.append({
                        "code": "PAPER_SUBMISSION_FAILED",
                        "blocking": True,
                        "detail": str(exc),
                    })

        effective_order = existing_order or submitted_order
        submission_payload = {
            "stage": "V140.11",
            "client_order_id": client_order_id,
            "submission_allowed": submission_allowed,
            "duplicate_order": duplicate_order,
            "broker_order_id": effective_order.get("id", ""),
            "broker_order_status": effective_order.get("status", ""),
            "actual_paper_orders_submitted": paper_orders_submitted,
            "network_requests_executed": network_requests,
            "write_requests_executed": write_requests,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(submission_result_path, submission_payload)

        reconciliation_verified = False
        if integration_required:
            try:
                reconciliation = _load_json(reconciliation_snapshot_path)
            except Exception as exc:
                reconciliation = {}
                issues.append({
                    "code": "INVALID_RECONCILIATION_SNAPSHOT",
                    "blocking": True,
                    "detail": str(exc),
                })
            if not reconciliation:
                issues.append({
                    "code": "RECONCILIATION_SNAPSHOT_NOT_FOUND",
                    "blocking": True,
                    "detail": str(reconciliation_snapshot_path),
                })
            else:
                expected_client_id = str(
                    reconciliation.get("client_order_id", client_order_id)
                ).strip()
                expected_open_orders = int(
                    reconciliation.get("expected_open_order_count", len(orders))
                )
                expected_positions = int(
                    reconciliation.get("expected_position_count", len(positions))
                )
                checks = [
                    (
                        "RECONCILIATION_CLIENT_ID_MISMATCH",
                        expected_client_id == client_order_id,
                    ),
                    (
                        "RECONCILIATION_OPEN_ORDER_MISMATCH",
                        expected_open_orders == len(orders),
                    ),
                    (
                        "RECONCILIATION_POSITION_MISMATCH",
                        expected_positions == len(positions),
                    ),
                ]
                for code, passed in checks:
                    if not passed:
                        issues.append({
                            "code": code,
                            "blocking": True,
                            "detail": "paper reconciliation failed",
                        })
                reconciliation_verified = all(passed for _, passed in checks)

        reconciliation_payload = {
            "stage": "V140.12",
            "client_order_id": client_order_id,
            "reconciliation_verified": reconciliation_verified,
            "open_order_count": len(orders),
            "position_count": len(positions),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(reconciliation_result_path, reconciliation_payload)

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        paper_integration_ready = bool(
            integration_required
            and endpoint_verified
            and broker_read_verified
            and reconciliation_verified
            and not safe_mode
        )

        if safe_mode:
            state, status = "PAPER_INTEGRATION_SAFE_MODE", "BLOCKED"
        elif paper_integration_ready and enable_network and enable_submission:
            state, status = "ACTUAL_PAPER_AUTONOMOUS_READY", "PASS"
        elif paper_integration_ready:
            state, status = "PAPER_INTEGRATION_READY_SUBMISSION_DISABLED", "PASS"
        else:
            state, status = "WAIT_AUTONOMOUS_ENGINE", "PASS"

        result = {
            "actual_credentials_used": credentials_used,
            "actual_external_network_used": network_requests > 0,
            "actual_paper_orders_submitted": paper_orders_submitted,
            "blocking_issue_count": blocking,
            "broker_read_verified": broker_read_verified,
            "client_order_id": client_order_id,
            "duplicate_order": duplicate_order,
            "endpoint_verified": endpoint_verified,
            "engine_id": engine_id,
            "implementation_type": "ALPACA_PAPER_INTEGRATION_BUNDLE",
            "issue_count": len(issues),
            "issues": issues,
            "live_orders_submitted": 0,
            "network_requests_executed": network_requests,
            "next_phase": (
                "V141_01_TO_V141_05"
                if paper_integration_ready
                else "V140_10_TO_V140_12_WAIT_AUTONOMOUS_ENGINE"
            ),
            "paper_integration_ready": paper_integration_ready,
            "reconciliation_verified": reconciliation_verified,
            "stage_range": "V140.10-V140.12",
            "state": state,
            "status": status,
            "submission_enabled": enable_submission,
            "submission_result_path": str(submission_result_path.resolve()),
            "safe_mode_engaged": safe_mode,
            "validation_mode": (
                "ACTUAL_ALPACA_PAPER"
                if enable_network
                else "LOCAL_ALPACA_PAPER_SNAPSHOT_ONLY"
            ),
            "write_requests_executed": write_requests,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "result_path": str(final_result_path.resolve()),
        }
        _write_json(final_result_path, result)
        return result
