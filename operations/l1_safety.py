from __future__ import annotations
from dataclasses import dataclass
import os
from typing import Any


PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"


@dataclass(frozen=True)
class LiveSafetyPolicy:
    paper_key_present: bool
    live_key_present: bool
    paper_base_url: str
    live_base_url: str
    live_network_enabled: bool
    live_write_enabled: bool
    live_confirmation: str
    maximum_live_order_notional: float
    maximum_live_daily_orders: int
    allowed_live_symbols: tuple[str, ...]

    def evaluate(self) -> dict[str, Any]:
        checks = {
            "paper_live_keys_separated": (
                not self.paper_key_present
                or not self.live_key_present
                or os.getenv("APCA_API_KEY_ID", "")
                != os.getenv("LIVE_APCA_API_KEY_ID", "")
            ),
            "paper_endpoint_valid": (
                self.paper_base_url == PAPER_BASE_URL
            ),
            "live_endpoint_valid": (
                self.live_base_url == LIVE_BASE_URL
            ),
            "live_network_disabled": (
                self.live_network_enabled is False
            ),
            "live_write_disabled": (
                self.live_write_enabled is False
            ),
            "live_confirmation_absent": (
                self.live_confirmation == ""
            ),
            "live_order_limit_safe": (
                0 < self.maximum_live_order_notional <= 100
            ),
            "live_daily_limit_safe": (
                1 <= self.maximum_live_daily_orders <= 10
            ),
            "live_symbols_restricted": (
                1 <= len(self.allowed_live_symbols) <= 3
            ),
        }
        return {
            "stage": "L1_PREPARATION",
            "status": (
                "PASS" if all(checks.values()) else "FAIL"
            ),
            "checks": checks,
            "failed": [
                key for key, passed in checks.items() if not passed
            ],
            "live_activation_allowed": False,
            "live_network_enabled": False,
            "live_write_enabled": False,
            "actual_live_orders_submitted": 0,
            "paper_completion_required": True,
        }


def load_live_safety_policy() -> LiveSafetyPolicy:
    symbols = tuple(
        value.strip().upper()
        for value in os.getenv(
            "LIVE_ALLOWED_SYMBOLS",
            "SPY",
        ).split(",")
        if value.strip()
    )
    return LiveSafetyPolicy(
        paper_key_present=bool(os.getenv("APCA_API_KEY_ID", "")),
        live_key_present=bool(os.getenv("LIVE_APCA_API_KEY_ID", "")),
        paper_base_url=os.getenv(
            "APCA_API_BASE_URL",
            PAPER_BASE_URL,
        ),
        live_base_url=os.getenv(
            "LIVE_APCA_API_BASE_URL",
            LIVE_BASE_URL,
        ),
        live_network_enabled=False,
        live_write_enabled=False,
        live_confirmation="",
        maximum_live_order_notional=float(
            os.getenv("LIVE_MAX_ORDER_NOTIONAL", "10")
        ),
        maximum_live_daily_orders=int(
            os.getenv("LIVE_MAX_DAILY_ORDERS", "1")
        ),
        allowed_live_symbols=symbols,
    )
