from __future__ import annotations
from typing import Any

PROFILES: dict[str,dict[str,Any]] = {
    "MOCK_READ_ONLY": {
        "account_read": True,
        "positions_read": True,
        "orders_read": True,
        "market_data_read": False,
        "network_required": False,
        "credentials_required": False,
        "order_submit": False,
        "order_cancel": False,
        "order_replace": False,
        "fund_transfer": False,
        "read_only": True,
    },
    "ALPACA_READ_ONLY": {
        "account_read": True,
        "positions_read": True,
        "orders_read": True,
        "market_data_read": True,
        "network_required": True,
        "credentials_required": True,
        "order_submit": False,
        "order_cancel": False,
        "order_replace": False,
        "fund_transfer": False,
        "read_only": True,
    },
    "IBKR_READ_ONLY": {
        "account_read": True,
        "positions_read": True,
        "orders_read": True,
        "market_data_read": True,
        "network_required": True,
        "credentials_required": True,
        "order_submit": False,
        "order_cancel": False,
        "order_replace": False,
        "fund_transfer": False,
        "read_only": True,
    },
    "ETRADE_READ_ONLY": {
        "account_read": True,
        "positions_read": True,
        "orders_read": True,
        "market_data_read": True,
        "network_required": True,
        "credentials_required": True,
        "order_submit": False,
        "order_cancel": False,
        "order_replace": False,
        "fund_transfer": False,
        "read_only": True,
    },
}

def get_capabilities(adapter_name: str) -> dict[str, Any]:
    return dict(PROFILES.get(adapter_name, PROFILES["MOCK_READ_ONLY"]))

def validate_read_only(capabilities: dict[str, Any]) -> dict[str, Any]:
    checks={
        "read_only":capabilities.get("read_only") is True,
        "order_submit_disabled":capabilities.get("order_submit") is False,
        "order_cancel_disabled":capabilities.get("order_cancel") is False,
        "order_replace_disabled":capabilities.get("order_replace") is False,
        "fund_transfer_disabled":capabilities.get("fund_transfer") is False,
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {"passed":not failed,"checks":checks,"failed":failed}
