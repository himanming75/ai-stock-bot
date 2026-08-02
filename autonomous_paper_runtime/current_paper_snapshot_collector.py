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


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _default_get(
    *,
    url: str,
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[int, Any]:
    request = urllib.request.Request(
        url=url,
        headers={**headers, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
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


class CurrentPaperSnapshotCollector:
    def run(
        self,
        *,
        output_path: Path,
        result_path: Path,
        enable_network: bool = False,
        base_url: str = PAPER_BASE_URL,
        timeout_seconds: int = 10,
        transport: Callable[..., tuple[int, Any]] | None = None,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        endpoint_verified = base_url.rstrip("/") == PAPER_BASE_URL
        if not endpoint_verified:
            issues.append({
                "code": "LIVE_OR_UNKNOWN_ENDPOINT_BLOCKED",
                "blocking": True,
                "detail": base_url,
            })

        credentials_configured = bool(
            os.getenv("APCA_API_KEY_ID", "").strip()
            and os.getenv("APCA_API_SECRET_KEY", "").strip()
        )
        if enable_network and not credentials_configured:
            issues.append({
                "code": "PAPER_CREDENTIALS_NOT_CONFIGURED",
                "blocking": True,
                "detail": "",
            })

        if not 3 <= int(timeout_seconds) <= 30:
            issues.append({
                "code": "TIMEOUT_INVALID",
                "blocking": True,
                "detail": str(timeout_seconds),
            })

        account: dict[str, Any] = {}
        positions: list[dict[str, Any]] = []
        open_orders: list[dict[str, Any]] = []
        clock: dict[str, Any] = {}
        account_http_status = 0
        positions_http_status = 0
        orders_http_status = 0
        clock_http_status = 0
        network_requests = 0

        ready_for_read = bool(
            enable_network
            and endpoint_verified
            and credentials_configured
            and not any(item.get("blocking") for item in issues)
        )

        if ready_for_read:
            getter = transport or _default_get
            headers = {
                "APCA-API-KEY-ID": os.environ[
                    "APCA_API_KEY_ID"
                ].strip(),
                "APCA-API-SECRET-KEY": os.environ[
                    "APCA_API_SECRET_KEY"
                ].strip(),
            }

            account_http_status, account_payload = getter(
                url=PAPER_BASE_URL + "/v2/account",
                headers=headers,
                timeout_seconds=timeout_seconds,
            )
            network_requests += 1
            if isinstance(account_payload, dict):
                account = account_payload

            positions_http_status, positions_payload = getter(
                url=PAPER_BASE_URL + "/v2/positions",
                headers=headers,
                timeout_seconds=timeout_seconds,
            )
            network_requests += 1
            if isinstance(positions_payload, list):
                positions = [
                    item for item in positions_payload
                    if isinstance(item, dict)
                ]

            orders_http_status, orders_payload = getter(
                url=PAPER_BASE_URL + "/v2/orders?status=open&limit=100",
                headers=headers,
                timeout_seconds=timeout_seconds,
            )
            network_requests += 1
            if isinstance(orders_payload, list):
                open_orders = [
                    item for item in orders_payload
                    if isinstance(item, dict)
                ]

            clock_http_status, clock_payload = getter(
                url=PAPER_BASE_URL + "/v2/clock",
                headers=headers,
                timeout_seconds=timeout_seconds,
            )
            network_requests += 1
            if isinstance(clock_payload, dict):
                clock = clock_payload

            for name, status in (
                ("ACCOUNT", account_http_status),
                ("POSITIONS", positions_http_status),
                ("OPEN_ORDERS", orders_http_status),
                ("CLOCK", clock_http_status),
            ):
                if not 200 <= status < 300:
                    issues.append({
                        "code": f"{name}_READ_FAILED",
                        "blocking": True,
                        "detail": str(status),
                    })

        blocking = sum(
            1 for item in issues if item.get("blocking")
        )
        safe_mode = blocking > 0
        observed_at = datetime.now(timezone.utc).isoformat()
        snapshot_written = False

        if ready_for_read and not safe_mode:
            snapshot = {
                "snapshot_type": "ACTUAL_ALPACA_PAPER_READ_ONLY",
                "observed_at": observed_at,
                "paper_only": True,
                "read_only": True,
                "account": account,
                "positions": positions,
                "open_orders": open_orders,
                "clock": clock,
                "source_http_status": {
                    "account": account_http_status,
                    "positions": positions_http_status,
                    "open_orders": orders_http_status,
                    "clock": clock_http_status,
                },
            }
            _write(output_path, snapshot)
            snapshot_written = True

        if safe_mode:
            state, status = (
                "CURRENT_PAPER_SNAPSHOT_SAFE_MODE",
                "BLOCKED",
            )
        elif snapshot_written:
            state, status = (
                "CURRENT_PAPER_SNAPSHOT_READY",
                "PASS",
            )
        else:
            state, status = (
                "WAIT_CURRENT_PAPER_SNAPSHOT_NETWORK_READ",
                "PASS",
            )

        result = {
            "stage": "DASH2.05",
            "implementation_type": (
                "CURRENT_PAPER_SNAPSHOT_COLLECTOR"
            ),
            "status": status,
            "state": state,
            "endpoint_verified": endpoint_verified,
            "credentials_configured": credentials_configured,
            "enable_network": enable_network,
            "snapshot_written": snapshot_written,
            "snapshot_path": str(output_path.resolve()),
            "account_http_status": account_http_status,
            "positions_http_status": positions_http_status,
            "orders_http_status": orders_http_status,
            "clock_http_status": clock_http_status,
            "account_status": account.get("status", ""),
            "position_count": len(positions),
            "open_order_count": len(open_orders),
            "market_open": bool(clock.get("is_open", False)),
            "paper_only": True,
            "read_only": True,
            "order_write_enabled": False,
            "cancel_enabled": False,
            "replace_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": ready_for_read,
            "actual_external_network_used": network_requests > 0,
            "network_requests_executed": network_requests,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "observed_at": observed_at,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
