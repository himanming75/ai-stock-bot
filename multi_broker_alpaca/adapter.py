from __future__ import annotations
from multi_broker_core.adapter import BrokerAdapter
from multi_broker_core.capabilities import BrokerCapabilities
from multi_broker_core.models import AccountSnapshot, OrderSnapshot, PositionSnapshot
from multi_broker_core.symbols import normalize_equity_symbol

from .mappers import map_account, map_order, map_position
from .transport import ReadOnlyTransport


class AlpacaReadOnlyAdapter(BrokerAdapter):
    def __init__(self, transport: ReadOnlyTransport) -> None:
        self.transport = transport
        self._account_cache: AccountSnapshot | None = None

    @property
    def broker_name(self) -> str:
        return "ALPACA"

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker="ALPACA",
            account_read=True,
            positions_read=True,
            orders_read=True,
            market_data_read=False,
            paper_trading=True,
            order_submission=False,
            order_cancel=False,
            fractional_shares=True,
            extended_hours=True,
            options=True,
            streaming=False,
        )

    def normalize_symbol(self, symbol: str) -> str:
        return normalize_equity_symbol(symbol)

    def get_account(self) -> AccountSnapshot:
        account = map_account(self.transport.get_json("/v2/account"))
        self._account_cache = account
        return account

    def _account_id(self) -> str:
        return (self._account_cache or self.get_account()).account_id

    def list_positions(self) -> list[PositionSnapshot]:
        payload = self.transport.get_json("/v2/positions")
        if not isinstance(payload, list):
            raise TypeError("Alpaca positions response must be a list")
        account_id = self._account_id()
        return [map_position(item, account_id) for item in payload]

    def list_orders(self) -> list[OrderSnapshot]:
        payload = self.transport.get_json("/v2/orders?status=all&limit=100&direction=desc")
        if not isinstance(payload, list):
            raise TypeError("Alpaca orders response must be a list")
        account_id = self._account_id()
        return [map_order(item, account_id) for item in payload]
