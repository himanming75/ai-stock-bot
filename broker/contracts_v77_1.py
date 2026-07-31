from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Mapping, Protocol, Sequence, runtime_checkable


class BrokerContractError(ValueError):
    """Raised when a broker request or snapshot violates the V77.1 contract."""


class BrokerEnvironment(str, Enum):
    OFFLINE = "offline"
    SANDBOX = "sandbox"
    LIVE = "live"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"


class BrokerOrderStatus(str, Enum):
    CREATED = "created"
    VALIDATED = "validated"
    REJECTED = "rejected"
    SUBMISSION_BLOCKED = "submission_blocked"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCEL_PENDING = "cancel_pending"
    CANCELED = "canceled"
    EXPIRED = "expired"
    ERROR = "error"


TERMINAL_ORDER_STATUSES = frozenset(
    {
        BrokerOrderStatus.REJECTED,
        BrokerOrderStatus.SUBMISSION_BLOCKED,
        BrokerOrderStatus.FILLED,
        BrokerOrderStatus.CANCELED,
        BrokerOrderStatus.EXPIRED,
        BrokerOrderStatus.ERROR,
    }
)


def _positive_decimal(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal):
        raise BrokerContractError(f"{name} must be Decimal")
    if not value.is_finite() or value <= 0:
        raise BrokerContractError(f"{name} must be finite and greater than zero")


def _non_negative_decimal(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal):
        raise BrokerContractError(f"{name} must be Decimal")
    if not value.is_finite() or value < 0:
        raise BrokerContractError(f"{name} must be finite and non-negative")


def normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if not value or len(value) > 15:
        raise BrokerContractError("symbol must contain 1-15 characters")
    if not all(ch.isalnum() or ch in {".", "-"} for ch in value):
        raise BrokerContractError("symbol contains unsupported characters")
    return value


@dataclass(frozen=True)
class BrokerSafetyPolicy:
    environment: BrokerEnvironment = BrokerEnvironment.OFFLINE
    network_allowed: bool = False
    order_submission_allowed: bool = False
    live_trading_authorized: bool = False
    allow_fractional_quantity: bool = False

    def validate(self) -> None:
        if self.environment is BrokerEnvironment.LIVE:
            raise BrokerContractError("V77.1 forbids live broker environment")
        if self.network_allowed:
            raise BrokerContractError("V77.1 requires network_allowed=false")
        if self.order_submission_allowed:
            raise BrokerContractError("V77.1 requires order_submission_allowed=false")
        if self.live_trading_authorized:
            raise BrokerContractError("V77.1 requires live_trading_authorized=false")


@dataclass(frozen=True)
class BrokerCapabilities:
    supports_market_orders: bool
    supports_limit_orders: bool
    supports_stop_orders: bool
    supports_stop_limit_orders: bool
    supports_fractional_quantity: bool
    supports_cancel: bool
    supports_replace: bool
    supported_time_in_force: tuple[TimeInForce, ...]
    environment: BrokerEnvironment

    def validate(self) -> None:
        if self.environment is BrokerEnvironment.LIVE:
            raise BrokerContractError("live capabilities are forbidden in V77.1")
        if not self.supported_time_in_force:
            raise BrokerContractError("at least one time-in-force value is required")
        if len(set(self.supported_time_in_force)) != len(self.supported_time_in_force):
            raise BrokerContractError("supported_time_in_force contains duplicates")


@dataclass(frozen=True)
class BrokerOrderRequest:
    client_order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    time_in_force: TimeInForce
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    strategy_id: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validate(self, policy: BrokerSafetyPolicy | None = None) -> None:
        if not self.client_order_id.strip():
            raise BrokerContractError("client_order_id is required")
        if len(self.client_order_id) > 64:
            raise BrokerContractError("client_order_id exceeds 64 characters")
        normalize_symbol(self.symbol)
        _positive_decimal(self.quantity, "quantity")

        if policy is not None:
            policy.validate()
            if not policy.allow_fractional_quantity and self.quantity != self.quantity.to_integral_value():
                raise BrokerContractError("fractional quantity is disabled")

        if self.order_type is OrderType.MARKET:
            if self.limit_price is not None or self.stop_price is not None:
                raise BrokerContractError("market orders cannot have limit_price or stop_price")
        elif self.order_type is OrderType.LIMIT:
            if self.limit_price is None:
                raise BrokerContractError("limit order requires limit_price")
            _positive_decimal(self.limit_price, "limit_price")
            if self.stop_price is not None:
                raise BrokerContractError("limit order cannot have stop_price")
        elif self.order_type is OrderType.STOP:
            if self.stop_price is None:
                raise BrokerContractError("stop order requires stop_price")
            _positive_decimal(self.stop_price, "stop_price")
            if self.limit_price is not None:
                raise BrokerContractError("stop order cannot have limit_price")
        elif self.order_type is OrderType.STOP_LIMIT:
            if self.stop_price is None or self.limit_price is None:
                raise BrokerContractError("stop-limit order requires stop_price and limit_price")
            _positive_decimal(self.stop_price, "stop_price")
            _positive_decimal(self.limit_price, "limit_price")


@dataclass(frozen=True)
class BrokerOrder:
    broker_order_id: str
    request: BrokerOrderRequest
    status: BrokerOrderStatus
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    submitted_at_utc: datetime | None
    updated_at_utc: datetime
    rejection_reason: str | None = None

    def validate(self) -> None:
        self.request.validate()
        _non_negative_decimal(self.filled_quantity, "filled_quantity")
        if self.filled_quantity > self.request.quantity:
            raise BrokerContractError("filled_quantity exceeds requested quantity")
        if self.average_fill_price is not None:
            _positive_decimal(self.average_fill_price, "average_fill_price")
        if self.status in {BrokerOrderStatus.ACCEPTED, BrokerOrderStatus.PARTIALLY_FILLED,
                           BrokerOrderStatus.FILLED, BrokerOrderStatus.CANCEL_PENDING,
                           BrokerOrderStatus.CANCELED, BrokerOrderStatus.EXPIRED}:
            if not self.broker_order_id.strip():
                raise BrokerContractError("broker_order_id is required after acceptance")
            if self.submitted_at_utc is None:
                raise BrokerContractError("submitted_at_utc is required after acceptance")
        if self.status is BrokerOrderStatus.PARTIALLY_FILLED:
            if not (Decimal("0") < self.filled_quantity < self.request.quantity):
                raise BrokerContractError("partial fill quantity is invalid")
        if self.status is BrokerOrderStatus.FILLED and self.filled_quantity != self.request.quantity:
            raise BrokerContractError("filled order must equal requested quantity")
        if self.status is BrokerOrderStatus.REJECTED and not self.rejection_reason:
            raise BrokerContractError("rejected order requires rejection_reason")


@dataclass(frozen=True)
class BrokerPosition:
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal

    def validate(self) -> None:
        normalize_symbol(self.symbol)
        if not isinstance(self.quantity, Decimal) or not self.quantity.is_finite():
            raise BrokerContractError("position quantity must be finite Decimal")
        _non_negative_decimal(self.average_entry_price, "average_entry_price")
        if not isinstance(self.market_value, Decimal) or not self.market_value.is_finite():
            raise BrokerContractError("market_value must be finite Decimal")
        if not isinstance(self.unrealized_pnl, Decimal) or not self.unrealized_pnl.is_finite():
            raise BrokerContractError("unrealized_pnl must be finite Decimal")


@dataclass(frozen=True)
class AccountSnapshot:
    account_id_masked: str
    currency: str
    cash: Decimal
    buying_power: Decimal
    equity: Decimal
    positions: tuple[BrokerPosition, ...]
    open_orders: tuple[BrokerOrder, ...]
    captured_at_utc: datetime

    def validate(self) -> None:
        if not self.account_id_masked.strip():
            raise BrokerContractError("account_id_masked is required")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise BrokerContractError("currency must be a three-letter code")
        for name, value in (
            ("cash", self.cash),
            ("buying_power", self.buying_power),
            ("equity", self.equity),
        ):
            _non_negative_decimal(value, name)
        for position in self.positions:
            position.validate()
        for order in self.open_orders:
            order.validate()
            if order.status in TERMINAL_ORDER_STATUSES:
                raise BrokerContractError("open_orders cannot include terminal orders")


@dataclass(frozen=True)
class BrokerHealth:
    environment: BrokerEnvironment
    adapter_name: str
    connected: bool
    authenticated: bool
    network_used: bool
    checked_at_utc: datetime
    details: Mapping[str, str] = field(default_factory=dict)

    def validate(self, policy: BrokerSafetyPolicy) -> None:
        policy.validate()
        if self.environment is BrokerEnvironment.LIVE:
            raise BrokerContractError("live broker health is forbidden")
        if self.network_used:
            raise BrokerContractError("network use is forbidden in V77.1")
        if self.connected or self.authenticated:
            raise BrokerContractError("V77.1 contract verification must remain disconnected")


@runtime_checkable
class BrokerContract(Protocol):
    """Contract every future sandbox broker adapter must implement."""

    @property
    def capabilities(self) -> BrokerCapabilities:
        ...

    def health(self) -> BrokerHealth:
        ...

    def get_account_snapshot(self) -> AccountSnapshot:
        ...

    def list_orders(self) -> Sequence[BrokerOrder]:
        ...

    def get_order(self, broker_order_id: str) -> BrokerOrder | None:
        ...

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrder:
        ...

    def cancel_order(self, broker_order_id: str) -> BrokerOrder:
        ...


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
