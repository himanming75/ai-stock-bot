from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import os

from alpaca_paper_read.config import PAPER_BASE_URL


@dataclass(frozen=True)
class ExecutionConfig:
    api_key: str
    secret_key: str
    base_url: str
    network_enabled: bool
    write_enabled: bool
    confirmation: str
    maximum_order_notional: Decimal
    maximum_daily_orders: int
    allowed_symbols: frozenset[str]
    timeout_seconds: float
    maximum_attempts: int
    backoff_seconds: float

    @property
    def credentials_present(self) -> bool:
        return bool(self.api_key.strip() and self.secret_key.strip())

    @property
    def paper_endpoint_enforced(self) -> bool:
        return self.base_url.rstrip("/") == PAPER_BASE_URL

    @property
    def explicit_confirmation_valid(self) -> bool:
        return self.confirmation == "I_UNDERSTAND_THIS_SUBMITS_A_PAPER_ORDER"


def _true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def load_execution_config() -> ExecutionConfig:
    base_url = os.getenv("APCA_API_BASE_URL", PAPER_BASE_URL).strip().rstrip("/")
    if base_url != PAPER_BASE_URL:
        raise ValueError("ONLY_ALPACA_PAPER_ENDPOINT_ALLOWED")

    maximum_order_notional = Decimal(
        os.getenv("P2_MAX_ORDER_NOTIONAL", "10")
    )
    maximum_daily_orders = int(os.getenv("P2_MAX_DAILY_ORDERS", "3"))
    allowed_symbols = frozenset(
        value.strip().upper()
        for value in os.getenv("P2_ALLOWED_SYMBOLS", "AAPL,MSFT,SPY").split(",")
        if value.strip()
    )

    if maximum_order_notional <= 0 or maximum_order_notional > Decimal("1000"):
        raise ValueError("P2_MAX_ORDER_NOTIONAL_OUT_OF_RANGE")
    if maximum_daily_orders < 1 or maximum_daily_orders > 100:
        raise ValueError("P2_MAX_DAILY_ORDERS_OUT_OF_RANGE")
    if not allowed_symbols:
        raise ValueError("P2_ALLOWED_SYMBOLS_EMPTY")

    return ExecutionConfig(
        api_key=os.getenv("APCA_API_KEY_ID", ""),
        secret_key=os.getenv("APCA_API_SECRET_KEY", ""),
        base_url=base_url,
        network_enabled=_true("ALPACA_PAPER_EXECUTION_NETWORK_ENABLE"),
        write_enabled=_true("ALPACA_PAPER_EXECUTION_WRITE_ENABLE"),
        confirmation=os.getenv("ALPACA_PAPER_EXECUTION_CONFIRMATION", ""),
        maximum_order_notional=maximum_order_notional,
        maximum_daily_orders=maximum_daily_orders,
        allowed_symbols=allowed_symbols,
        timeout_seconds=float(
            os.getenv("ALPACA_PAPER_EXECUTION_TIMEOUT_SECONDS", "10")
        ),
        maximum_attempts=int(
            os.getenv("ALPACA_PAPER_EXECUTION_MAX_ATTEMPTS", "2")
        ),
        backoff_seconds=float(
            os.getenv("ALPACA_PAPER_EXECUTION_BACKOFF_SECONDS", "0.5")
        ),
    )
