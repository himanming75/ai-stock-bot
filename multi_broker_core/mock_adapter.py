from __future__ import annotations
from decimal import Decimal
from .adapter import BrokerAdapter
from .capabilities import BrokerCapabilities
from .models import AccountSnapshot, OrderSnapshot, PositionSnapshot
from .symbols import normalize_equity_symbol


class MockBrokerAdapter(BrokerAdapter):
    def __init__(self, account_id: str = "MOCK-001") -> None:
        self._account_id = account_id

    @property
    def broker_name(self) -> str:
        return "MOCK"

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker="MOCK", account_read=True, positions_read=True, orders_read=True,
            market_data_read=False, paper_trading=True, order_submission=False,
            order_cancel=False, fractional_shares=True, extended_hours=False,
            options=False, streaming=False,
        )

    def normalize_symbol(self, symbol: str) -> str:
        return normalize_equity_symbol(symbol)

    def get_account(self) -> AccountSnapshot:
        return AccountSnapshot(
            broker="MOCK", account_id=self._account_id, currency="USD",
            equity=Decimal("100000"), cash=Decimal("75000"),
            buying_power=Decimal("150000"), status="ACTIVE",
        )

    def list_positions(self) -> list[PositionSnapshot]:
        return [
            PositionSnapshot(
                broker="MOCK", account_id=self._account_id, symbol="SPY",
                quantity=Decimal("10"), average_price=Decimal("500"),
                market_value=Decimal("5050"), unrealized_pl=Decimal("50"),
            )
        ]

    def list_orders(self) -> list[OrderSnapshot]:
        return []
