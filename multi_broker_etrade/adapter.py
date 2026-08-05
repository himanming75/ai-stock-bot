from __future__ import annotations
from multi_broker_core.adapter import BrokerAdapter
from multi_broker_core.capabilities import BrokerCapabilities
from multi_broker_core.models import AccountSnapshot, OrderSnapshot, PositionSnapshot
from multi_broker_core.symbols import normalize_equity_symbol

from .mappers import map_account, map_order, map_position
from .token_state import ETradeTokenState, initial_token_state
from .transport import ETradeReadOnlyTransport


class ETradeReadOnlyAdapter(BrokerAdapter):
    def __init__(
        self,
        transport: ETradeReadOnlyTransport,
        account_id_key: str | None = None,
    ) -> None:
        self.transport = transport
        self.account_id_key = account_id_key
        self._account_cache: AccountSnapshot | None = None
        self._token_state = initial_token_state()

    @property
    def broker_name(self) -> str:
        return "ETRADE"

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker="ETRADE",
            account_read=True,
            positions_read=True,
            orders_read=True,
            market_data_read=False,
            paper_trading=False,
            order_submission=False,
            order_cancel=False,
            fractional_shares=False,
            extended_hours=False,
            options=True,
            streaming=False,
        )

    @property
    def token_state(self) -> ETradeTokenState:
        return self._token_state

    def normalize_symbol(self, symbol: str) -> str:
        return normalize_equity_symbol(symbol)

    def _accounts(self) -> list[dict]:
        payload = self.transport.get_json("/v1/accounts/list.json")
        response = payload.get("AccountListResponse", payload)
        accounts = response.get("Accounts", {}).get("Account", [])
        if isinstance(accounts, dict):
            accounts = [accounts]
        if not isinstance(accounts, list):
            raise TypeError("E*TRADE accounts response must contain a list")
        return accounts

    def _selected_account(self) -> dict:
        accounts = self._accounts()
        if not accounts:
            raise RuntimeError("No E*TRADE accounts returned")
        if self.account_id_key:
            for account in accounts:
                if str(account.get("accountIdKey")) == self.account_id_key:
                    return account
            raise KeyError(f"E*TRADE accountIdKey not found: {self.account_id_key}")
        return accounts[0]

    def get_account(self) -> AccountSnapshot:
        account = self._selected_account()
        account_id = str(account.get("accountIdKey"))
        balance_payload = self.transport.get_json(
            f"/v1/accounts/{account_id}/balance.json?instType=BROKERAGE&realTimeNAV=true"
        )
        balance_response = balance_payload.get("BalanceResponse", balance_payload)
        result = map_account(account, balance_response)
        self._account_cache = result
        return result

    def _account_id(self) -> str:
        return (self._account_cache or self.get_account()).account_id

    def list_positions(self) -> list[PositionSnapshot]:
        account_id = self._account_id()
        payload = self.transport.get_json(
            f"/v1/accounts/{account_id}/portfolio.json"
        )
        response = payload.get("PortfolioResponse", payload)
        accounts = response.get("AccountPortfolio", [])
        if isinstance(accounts, dict):
            accounts = [accounts]
        positions: list[dict] = []
        for account in accounts:
            values = account.get("Position", [])
            if isinstance(values, dict):
                values = [values]
            positions.extend(values)
        return [map_position(item, account_id) for item in positions]

    def list_orders(self) -> list[OrderSnapshot]:
        account_id = self._account_id()
        payload = self.transport.get_json(
            f"/v1/accounts/{account_id}/orders.json"
        )
        response = payload.get("OrdersResponse", payload)
        orders = response.get("Order", [])
        if isinstance(orders, dict):
            orders = [orders]
        return [map_order(item, account_id) for item in orders]
