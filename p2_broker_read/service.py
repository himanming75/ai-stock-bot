from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

from alpaca_paper_read.adapter import AlpacaPaperReadAdapter
from alpaca_paper_read.config import load_config
from alpaca_paper_read.http_client import ReadOnlyHttpClient


PAPER_ENDPOINT = "https://paper-api.alpaca.markets"


def _decimal_valid(value: Any) -> bool:
    try:
        return Decimal(str(value)) >= 0
    except (InvalidOperation, ValueError):
        return False


def _fingerprint(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _sanitize_account(account: dict[str, Any]) -> dict[str, Any]:
    account_id = str(account.get("id", ""))
    return {
        "account_id_fingerprint": _fingerprint(account_id),
        "status": account.get("status", ""),
        "currency": account.get("currency", ""),
        "cash": account.get("cash", "0"),
        "portfolio_value": account.get("portfolio_value", "0"),
        "equity": account.get("equity", "0"),
        "buying_power": account.get("buying_power", "0"),
        "trading_blocked": account.get("trading_blocked", False),
        "account_blocked": account.get("account_blocked", False),
        "pattern_day_trader": account.get("pattern_day_trader", False),
    }


def run(root: Path) -> dict[str, Any]:
    config = load_config()
    if not config.actual_network_enabled:
        raise RuntimeError("P2_ACTUAL_NETWORK_READ_NOT_CONFIRMED")
    if config.base_url != PAPER_ENDPOINT:
        raise RuntimeError("P2_PAPER_ENDPOINT_REQUIRED")

    adapter = AlpacaPaperReadAdapter(ReadOnlyHttpClient(config))

    account_raw = adapter.get_account()
    positions = adapter.get_positions()
    open_orders = adapter.get_open_orders()
    clock = adapter.get_clock()
    account = _sanitize_account(account_raw)

    checks = {
        "paper_endpoint_enforced": config.base_url == PAPER_ENDPOINT,
        "credentials_present": config.credentials_present,
        "account_response_present": bool(account_raw),
        "account_id_present": bool(account_raw.get("id")),
        "account_status_active": (
            str(account.get("status", "")).upper() == "ACTIVE"
        ),
        "cash_valid": _decimal_valid(account.get("cash")),
        "equity_valid": _decimal_valid(account.get("equity")),
        "buying_power_valid": _decimal_valid(account.get("buying_power")),
        "portfolio_value_valid": _decimal_valid(
            account.get("portfolio_value")
        ),
        "positions_response_list": isinstance(positions, list),
        "open_orders_response_list": isinstance(open_orders, list),
        "clock_response_present": bool(clock.get("timestamp")),
        "clock_is_open_boolean": isinstance(clock.get("is_open"), bool),
        "account_not_blocked": account.get("account_blocked") is False,
        "trading_not_blocked": account.get("trading_blocked") is False,
    }
    failed = [key for key, value in checks.items() if not value]
    passed = not failed

    result = {
        "stage": "P2_ACTUAL_PAPER_BROKER_READ_VALIDATION",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if passed else "FAIL",
        "validated": passed,
        "checks": checks,
        "failed": failed,
        "paper_endpoint": config.base_url,
        "account": account,
        "positions": positions,
        "open_orders": open_orders,
        "clock": clock,
        "position_count": len(positions),
        "open_order_count": len(open_orders),
        "actual_external_network_used": True,
        "actual_broker_read_performed": True,
        "actual_broker_read_request_count": 4,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_order_modification_performed": False,
        "actual_order_cancellation_performed": False,
        "actual_portfolio_modified": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "raw_credentials_printed": False,
        "raw_credentials_stored": False,
        "live_endpoint_used": False,
        "next_fixed_action": (
            "P3_ACTUAL_PAPER_ORDER_VALIDATION"
            if passed
            else "FIX_P2_FAILED_CHECKS"
        ),
    }

    actual = root / "release/p2_actual_paper_broker_read/actual"
    actual.mkdir(parents=True, exist_ok=True)
    (actual / "p2_actual_broker_read_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    certificate = {
        "certificate_stage": "P2_ACTUAL_PAPER_BROKER_READ",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "eligible": passed,
        "status": "PASS" if passed else "BLOCKED",
        "p2_actual_broker_read_validated": passed,
        "p3_actual_paper_order_allowed": False,
        "p3_development_allowed": passed,
        "live_validation_allowed": False,
        "live_order_submission_allowed": False,
        "actual_paper_orders_submitted_during_p2": 0,
        "actual_live_orders_submitted_during_p2": 0,
        "failed": failed,
    }
    (actual / "p2_actual_broker_read_certificate.json").write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
