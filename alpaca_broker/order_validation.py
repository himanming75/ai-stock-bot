from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
import time
from typing import Any, Callable

from portfolio_engine import PortfolioSnapshot

from .client import AlpacaPaperClient
from .errors import AlpacaConfigurationError
from .models import BrokerOrder
from .reconciliation import BrokerPortfolioReconciler


TERMINAL_ORDER_STATUSES = frozenset({
    "filled",
    "canceled",
    "expired",
    "rejected",
    "done_for_day",
})


@dataclass(frozen=True)
class OrderValidationPolicy:
    max_poll_attempts: int = 5
    poll_interval_seconds: float = 1.0
    require_terminal_status: bool = True

    def validate(self) -> None:
        if not 1 <= self.max_poll_attempts <= 20:
            raise AlpacaConfigurationError("max_poll_attempts must be between 1 and 20")
        if self.poll_interval_seconds < 0 or self.poll_interval_seconds > 30:
            raise AlpacaConfigurationError("poll_interval_seconds must be between 0 and 30")


@dataclass(frozen=True)
class ActualPaperOrderValidationReport:
    generated_at: datetime
    client_order_id: str
    broker_order_id: str
    symbol: str
    side: str
    requested_quantity: Decimal
    filled_quantity: Decimal
    final_status: str
    terminal_status_reached: bool
    poll_attempts: int
    account_status: str
    trading_blocked: bool
    position_quantity: Decimal
    reconciliation_matched: bool | None
    network_requests_executed: int
    write_requests_executed: int
    additional_orders_submitted: int
    live_orders_submitted: int = 0

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        for key, value in tuple(raw.items()):
            if isinstance(value, Decimal):
                raw[key] = str(value)
            elif isinstance(value, datetime):
                raw[key] = value.isoformat()
        return raw


class ActualPaperOrderValidator:
    """Read-only post-submission validator for one known Paper order."""

    def __init__(
        self,
        *,
        client: AlpacaPaperClient,
        policy: OrderValidationPolicy,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        policy.validate()
        if client.config.network_write_enabled:
            raise AlpacaConfigurationError(
                "order validation client must have write network disabled"
            )
        if not client.config.network_read_enabled:
            raise AlpacaConfigurationError(
                "order validation client requires read network"
            )
        self.client = client
        self.policy = policy
        self.sleep = sleep

    def poll_order(self, client_order_id: str) -> tuple[BrokerOrder, int]:
        if not client_order_id.startswith("BOT-PAPER-ONE-"):
            raise AlpacaConfigurationError("unexpected client_order_id prefix")

        last_order: BrokerOrder | None = None
        for attempt in range(1, self.policy.max_poll_attempts + 1):
            last_order = self.client.get_order_by_client_id(client_order_id)
            if last_order.status.lower() in TERMINAL_ORDER_STATUSES:
                return last_order, attempt
            if attempt < self.policy.max_poll_attempts:
                self.sleep(self.policy.poll_interval_seconds)

        assert last_order is not None
        if self.policy.require_terminal_status:
            raise AlpacaConfigurationError(
                f"order did not reach terminal status after {self.policy.max_poll_attempts} polls"
            )
        return last_order, self.policy.max_poll_attempts

    def validate(
        self,
        *,
        client_order_id: str,
        internal_portfolio: PortfolioSnapshot | None = None,
    ) -> ActualPaperOrderValidationReport:
        order, attempts = self.poll_order(client_order_id)
        account = self.client.get_account()
        positions = self.client.list_positions()

        matching_position = next(
            (position for position in positions if position.symbol == order.symbol),
            None,
        )
        position_quantity = (
            matching_position.quantity if matching_position is not None else Decimal("0")
        )

        reconciliation_matched = None
        if internal_portfolio is not None:
            reconciliation_matched = BrokerPortfolioReconciler().reconcile(
                internal=internal_portfolio,
                account=account,
                positions=positions,
            ).matched

        terminal = order.status.lower() in TERMINAL_ORDER_STATUSES
        return ActualPaperOrderValidationReport(
            generated_at=datetime.now(timezone.utc),
            client_order_id=order.client_order_id,
            broker_order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            requested_quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            final_status=order.status,
            terminal_status_reached=terminal,
            poll_attempts=attempts,
            account_status=account.status,
            trading_blocked=account.trading_blocked,
            position_quantity=position_quantity,
            reconciliation_matched=reconciliation_matched,
            network_requests_executed=self.client.network_requests_executed,
            write_requests_executed=self.client.write_requests_executed,
            additional_orders_submitted=0,
        )
