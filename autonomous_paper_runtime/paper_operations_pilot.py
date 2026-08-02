from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"


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


def _get_json(url: str, key: str, secret: str, timeout: int = 15) -> Any:
    request = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read().decode("utf-8")
        return json.loads(data) if data else {}


class PaperOperationsPilot:
    def run(
        self,
        *,
        final_release_result_path: Path,
        pilot_policy_path: Path,
        local_snapshot_path: Path,
        account_snapshot_path: Path,
        preflight_report_path: Path,
        pilot_token_path: Path,
        result_path: Path,
        base_url: str = PAPER_BASE_URL,
        enable_network: bool = False,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            release = _load(final_release_result_path)
        except Exception as exc:
            release = {}
            issues.append({"code": "INVALID_FINAL_RELEASE_RESULT", "blocking": True, "detail": str(exc)})

        if not release:
            issues.append({"code": "FINAL_RELEASE_RESULT_NOT_FOUND", "blocking": True, "detail": str(final_release_result_path)})

        release_status = str(release.get("status", "")).upper()
        release_state = str(release.get("state", "")).upper()
        release_safe = bool(release.get("safe_mode_engaged", False))
        final_ready = bool(release.get("final_production_package_ready", False))
        release_id = str(release.get("release_id", "")).strip()

        if release_status == "BLOCKED" or release_safe:
            issues.append({"code": "FINAL_RELEASE_SAFE_MODE", "blocking": True, "detail": release_state})

        required = final_ready or release_state == "V143_FINAL_PRODUCTION_PACKAGE_READY"

        try:
            policy = _load(pilot_policy_path) if required else {}
        except Exception as exc:
            policy = {}
            issues.append({"code": "INVALID_PILOT_POLICY", "blocking": True, "detail": str(exc)})

        if required and not policy:
            issues.append({"code": "PILOT_POLICY_NOT_FOUND", "blocking": True, "detail": str(pilot_policy_path)})

        endpoint_verified = base_url.rstrip("/") == PAPER_BASE_URL
        if required and not endpoint_verified:
            issues.append({"code": "NON_PAPER_ENDPOINT_BLOCKED", "blocking": True, "detail": base_url})

        policy_ready = False
        pilot_id = ""
        if policy:
            pilot_id = str(policy.get("pilot_id", "")).strip()
            checks = [
                ("PILOT_ID_MISSING", bool(pilot_id)),
                ("READ_ONLY_REQUIRED", bool(policy.get("read_only", False))),
                ("ORDER_SUBMISSION_MUST_BE_DISABLED", not bool(policy.get("order_submission_enabled", True))),
                ("LIVE_TRADING_MUST_BE_DISABLED", not bool(policy.get("live_trading_enabled", True))),
                ("MAX_DAILY_ORDERS_MUST_BE_ZERO", int(policy.get("max_daily_orders", -1)) == 0),
                ("PAPER_ENDPOINT_POLICY_REQUIRED", str(policy.get("expected_base_url", "")).rstrip("/") == PAPER_BASE_URL),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({"code": code, "blocking": True, "detail": "pilot policy gate failed"})
            policy_ready = all(passed for _, passed in checks)

        key = os.getenv("APCA_API_KEY_ID", "")
        secret = os.getenv("APCA_API_SECRET_KEY", "")
        credentials_present = bool(key and secret)
        credentials_used = False
        network_requests = 0

        account: dict[str, Any] = {}
        clock: dict[str, Any] = {}
        orders: list[Any] = []
        positions: list[Any] = []

        blocking_before_read = any(item.get("blocking") for item in issues)

        if required and endpoint_verified and policy_ready and not blocking_before_read:
            if enable_network:
                if not credentials_present:
                    issues.append({"code": "PAPER_CREDENTIALS_MISSING", "blocking": True, "detail": "APCA_API_KEY_ID and APCA_API_SECRET_KEY are required"})
                else:
                    credentials_used = True
                    try:
                        account = dict(_get_json(f"{PAPER_BASE_URL}/v2/account", key, secret))
                        network_requests += 1
                        clock = dict(_get_json(f"{PAPER_BASE_URL}/v2/clock", key, secret))
                        network_requests += 1
                        open_orders = _get_json(f"{PAPER_BASE_URL}/v2/orders?status=open", key, secret)
                        network_requests += 1
                        current_positions = _get_json(f"{PAPER_BASE_URL}/v2/positions", key, secret)
                        network_requests += 1
                        orders = list(open_orders) if isinstance(open_orders, list) else []
                        positions = list(current_positions) if isinstance(current_positions, list) else []
                    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TypeError) as exc:
                        issues.append({"code": "PAPER_READ_FAILED", "blocking": True, "detail": str(exc)})
            else:
                try:
                    snapshot = _load(local_snapshot_path)
                except Exception as exc:
                    snapshot = {}
                    issues.append({"code": "INVALID_LOCAL_PILOT_SNAPSHOT", "blocking": True, "detail": str(exc)})
                if not snapshot:
                    issues.append({"code": "LOCAL_PILOT_SNAPSHOT_NOT_FOUND", "blocking": True, "detail": str(local_snapshot_path)})
                else:
                    account = dict(snapshot.get("account", {}))
                    clock = dict(snapshot.get("clock", {}))
                    orders = list(snapshot.get("open_orders", []))
                    positions = list(snapshot.get("positions", []))

        account_ready = False
        if account:
            checks = [
                ("ACCOUNT_NOT_ACTIVE", str(account.get("status", "")).upper() == "ACTIVE"),
                ("ACCOUNT_BLOCKED", not bool(account.get("account_blocked", False))),
                ("TRADING_BLOCKED", not bool(account.get("trading_blocked", False))),
                ("NEGATIVE_EQUITY", float(account.get("equity", 0)) >= 0),
                ("NEGATIVE_CASH", float(account.get("cash", 0)) >= 0),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({"code": code, "blocking": True, "detail": "Paper account preflight failed"})
            account_ready = all(passed for _, passed in checks)

        snapshot_payload = {
            "stage": "OP1.02",
            "pilot_id": pilot_id,
            "account_status": account.get("status", ""),
            "cash": str(account.get("cash", "")),
            "equity": str(account.get("equity", "")),
            "buying_power": str(account.get("buying_power", "")),
            "market_is_open": bool(clock.get("is_open", False)),
            "open_order_count": len(orders),
            "position_count": len(positions),
            "network_mode": enable_network,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        _write(account_snapshot_path, snapshot_payload)

        blocking = sum(1 for item in issues if item.get("blocking"))
        preflight_ready = bool(required and endpoint_verified and policy_ready and account_ready and not blocking)

        preflight = {
            "stage": "OP1.03",
            "pilot_id": pilot_id,
            "release_id": release_id,
            "endpoint_verified": endpoint_verified,
            "credentials_present": credentials_present,
            "credentials_used": credentials_used,
            "account_ready": account_ready,
            "market_is_open": bool(clock.get("is_open", False)),
            "open_order_count": len(orders),
            "position_count": len(positions),
            "read_only": True,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "pilot_preflight_ready": preflight_ready,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _write(preflight_report_path, preflight)

        token_written = False
        duplicate_token = False
        if preflight_ready:
            token = {
                "stage": "OP1.04",
                "pilot_id": pilot_id,
                "release_id": release_id,
                "paper_operations_pilot_ready": True,
                "read_only": True,
                "order_submission_enabled": False,
                "live_trading_enabled": False,
                "broker_network_allowed_for_reads": bool(enable_network),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if pilot_token_path.exists():
                existing = _load(pilot_token_path)
                if existing.get("pilot_id") == pilot_id:
                    duplicate_token = True
                else:
                    issues.append({"code": "PILOT_TOKEN_CONFLICT", "blocking": True, "detail": "another pilot token exists"})
            else:
                _write(pilot_token_path, token)
                token_written = True

        blocking = sum(1 for item in issues if item.get("blocking"))
        safe_mode = blocking > 0
        pilot_ready = bool(preflight_ready and (token_written or duplicate_token) and not safe_mode)

        if safe_mode:
            out_state, out_status = "PAPER_OPERATIONS_PILOT_SAFE_MODE", "BLOCKED"
        elif pilot_ready:
            out_state, out_status = "PAPER_OPERATIONS_READ_ONLY_READY", "PASS"
        else:
            out_state, out_status = "WAIT_FINAL_PRODUCTION_PACKAGE", "PASS"

        result = {
            "stage_range": "OP1.01-OP1.04",
            "implementation_type": "PAPER_OPERATIONS_PILOT_BOOTSTRAP",
            "status": out_status,
            "state": out_state,
            "pilot_id": pilot_id,
            "release_id": release_id,
            "endpoint_verified": endpoint_verified,
            "policy_ready": policy_ready,
            "account_ready": account_ready,
            "pilot_preflight_ready": preflight_ready,
            "paper_operations_pilot_ready": pilot_ready,
            "pilot_token_written": token_written,
            "duplicate_pilot_token": duplicate_token,
            "read_only": True,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": credentials_used,
            "actual_external_network_used": network_requests > 0,
            "network_requests_executed": network_requests,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": "OP1_05_DAILY_READ_ONLY_OBSERVATION" if pilot_ready else "OP1_WAIT_FINAL_RELEASE",
            "validation_mode": "ACTUAL_PAPER_READ_ONLY" if enable_network else "LOCAL_PAPER_SNAPSHOT_ONLY",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
