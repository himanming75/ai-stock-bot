from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .client import AlpacaPaperClient
from .config import AlpacaPaperConfig, CredentialLoader
from .errors import AlpacaConfigurationError
from .models import BrokerOrder
from .transport import HttpTransport


WRITE_OPT_IN_ENV = "AI_STOCK_BOT_ENABLE_ALPACA_PAPER_SINGLE_ORDER"
WRITE_CONFIRMATION_ENV = "AI_STOCK_BOT_ALPACA_PAPER_ORDER_CONFIRMATION"
WRITE_CONFIRMATION_TEXT = "SUBMIT ONE ALPACA PAPER ORDER ONLY"
WRITE_SYMBOL_ENV = "AI_STOCK_BOT_ALPACA_PAPER_SYMBOL"
WRITE_SIDE_ENV = "AI_STOCK_BOT_ALPACA_PAPER_SIDE"
WRITE_QUANTITY_ENV = "AI_STOCK_BOT_ALPACA_PAPER_QUANTITY"
WRITE_MAX_NOTIONAL_ENV = "AI_STOCK_BOT_ALPACA_PAPER_MAX_NOTIONAL"

ALLOWED_SYMBOLS = frozenset({"AAPL", "SPY", "QQQ"})
MAX_QUANTITY = Decimal("1")
MAX_NOTIONAL = Decimal("100")


@dataclass(frozen=True)
class ControlledOrderPlan:
    symbol: str
    side: str
    quantity: Decimal
    reference_price: Decimal
    estimated_notional: Decimal
    client_order_id: str
    order_type: str = "market"
    time_in_force: str = "day"

    def validate(self) -> None:
        if self.symbol not in ALLOWED_SYMBOLS:
            raise AlpacaConfigurationError("symbol is not in the controlled allowlist")
        if self.side not in {"buy", "sell"}:
            raise AlpacaConfigurationError("side must be buy or sell")
        if self.quantity <= 0 or self.quantity > MAX_QUANTITY:
            raise AlpacaConfigurationError("quantity exceeds the controlled limit")
        if self.reference_price <= 0:
            raise AlpacaConfigurationError("reference_price must be positive")
        if self.estimated_notional > MAX_NOTIONAL:
            raise AlpacaConfigurationError("estimated notional exceeds $100")
        if self.order_type != "market" or self.time_in_force != "day":
            raise AlpacaConfigurationError("only market/day orders are allowed")
        if not self.client_order_id.startswith("BOT-PAPER-ONE-"):
            raise AlpacaConfigurationError("invalid controlled client_order_id")

    def payload(self) -> dict[str, str]:
        self.validate()
        return {
            "symbol": self.symbol,
            "qty": str(self.quantity),
            "side": self.side,
            "type": self.order_type,
            "time_in_force": self.time_in_force,
            "client_order_id": self.client_order_id,
        }


@dataclass(frozen=True)
class ControlledOrderReport:
    generated_at: datetime
    mode: str
    symbol: str
    side: str
    quantity: Decimal
    estimated_notional: Decimal
    client_order_id: str
    submitted: bool
    broker_order_id: str | None
    broker_status: str | None
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int = 0

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        for key, value in tuple(raw.items()):
            if isinstance(value, Decimal):
                raw[key] = str(value)
            elif isinstance(value, datetime):
                raw[key] = value.isoformat()
        return raw


class ControlledPaperOrderOptIn:
    def __init__(self, client: AlpacaPaperClient) -> None:
        self.client = client
        self._consumed = False

    @staticmethod
    def validate_opt_in(environ: dict[str, str]) -> None:
        if environ.get(WRITE_OPT_IN_ENV, "").strip().upper() != "YES":
            raise AlpacaConfigurationError(
                f"{WRITE_OPT_IN_ENV}=YES is required"
            )
        if environ.get(WRITE_CONFIRMATION_ENV, "").strip() != WRITE_CONFIRMATION_TEXT:
            raise AlpacaConfigurationError(
                f"{WRITE_CONFIRMATION_ENV} must equal: {WRITE_CONFIRMATION_TEXT}"
            )

    @classmethod
    def from_environment(
        cls,
        environ: dict[str, str],
        *,
        transport: HttpTransport,
        timeout_seconds: float = 10.0,
        max_retries: int = 0,
    ) -> "ControlledPaperOrderOptIn":
        cls.validate_opt_in(environ)
        key, secret = CredentialLoader().load(environ)
        config = AlpacaPaperConfig(
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            network_read_enabled=True,
            network_write_enabled=True,
        )
        return cls(AlpacaPaperClient(
            config=config,
            api_key=key,
            secret_key=secret,
            transport=transport,
        ))

    @staticmethod
    def build_plan(
        *,
        symbol: str,
        side: str,
        quantity: Decimal,
        reference_price: Decimal,
        client_order_id: str,
    ) -> ControlledOrderPlan:
        plan = ControlledOrderPlan(
            symbol=symbol.upper(),
            side=side.lower(),
            quantity=quantity,
            reference_price=reference_price,
            estimated_notional=quantity * reference_price,
            client_order_id=client_order_id,
        )
        plan.validate()
        return plan

    def preview(self, plan: ControlledOrderPlan) -> ControlledOrderReport:
        plan.validate()
        self.client.preview_submit_order(plan.payload())
        return ControlledOrderReport(
            generated_at=datetime.now(timezone.utc),
            mode="PREVIEW_ONLY",
            symbol=plan.symbol,
            side=plan.side,
            quantity=plan.quantity,
            estimated_notional=plan.estimated_notional,
            client_order_id=plan.client_order_id,
            submitted=False,
            broker_order_id=None,
            broker_status=None,
            network_requests_executed=self.client.network_requests_executed,
            write_requests_executed=self.client.write_requests_executed,
            actual_paper_orders_submitted=0,
        )

    def submit_once(self, plan: ControlledOrderPlan) -> ControlledOrderReport:
        if self._consumed:
            raise AlpacaConfigurationError("single-order opt-in already consumed")
        plan.validate()

        account = self.client.get_account()
        if account.status != "ACTIVE" or account.trading_blocked:
            raise AlpacaConfigurationError("paper account is not eligible for trading")

        clock = self.client.get_clock()
        if not clock.is_open:
            raise AlpacaConfigurationError("market is closed")

        open_orders = self.client.list_orders(status="open", limit=50)
        if open_orders:
            raise AlpacaConfigurationError("existing open orders must be cleared first")

        if plan.side == "buy":
            positions = self.client.list_positions()
            if any(position.symbol == plan.symbol for position in positions):
                raise AlpacaConfigurationError("symbol already has an open position")
            if plan.estimated_notional > account.cash:
                raise AlpacaConfigurationError("insufficient paper cash")

        order = self.client.submit_order(plan.payload())
        self._consumed = True
        return ControlledOrderReport(
            generated_at=datetime.now(timezone.utc),
            mode="ACTUAL_PAPER_SINGLE_ORDER",
            symbol=plan.symbol,
            side=plan.side,
            quantity=plan.quantity,
            estimated_notional=plan.estimated_notional,
            client_order_id=plan.client_order_id,
            submitted=True,
            broker_order_id=order.order_id,
            broker_status=order.status,
            network_requests_executed=self.client.network_requests_executed,
            write_requests_executed=self.client.write_requests_executed,
            actual_paper_orders_submitted=1,
        )
