from __future__ import annotations
from .capabilities import get_capabilities
from .factory import BrokerFactory


class ReadOnlyBrokerRouter:
    def __init__(self) -> None:
        self.adapters = {}

    def register(
        self,
        broker: str,
        *,
        snapshot: dict,
    ) -> None:
        name = broker.upper()
        self.adapters[name] = BrokerFactory.create(
            name,
            snapshot=snapshot,
        )

    def capabilities(self) -> dict:
        return {
            name: get_capabilities(name)
            for name in sorted(self.adapters)
        }

    def unified_snapshot(
        self,
        *,
        symbols: list[str] | None = None,
    ) -> dict:
        symbols = symbols or []
        brokers = {}
        accounts = []
        positions = []
        orders = []
        quotes = []
        for name, adapter in sorted(
            self.adapters.items()
        ):
            broker_accounts = adapter.accounts()
            broker_positions = adapter.positions()
            broker_orders = adapter.orders()
            broker_quotes = adapter.quotes(symbols)
            brokers[name] = {
                "account_count": len(broker_accounts),
                "position_count": len(broker_positions),
                "order_count": len(broker_orders),
                "quote_count": len(broker_quotes),
                "capabilities": get_capabilities(name),
            }
            accounts.extend(broker_accounts)
            positions.extend(broker_positions)
            orders.extend(broker_orders)
            quotes.extend(broker_quotes)

        return {
            "mode": "READ_ONLY",
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "brokers": brokers,
            "accounts": accounts,
            "positions": positions,
            "orders": orders,
            "quotes": quotes,
            "totals": {
                "brokers": len(brokers),
                "accounts": len(accounts),
                "positions": len(positions),
                "orders": len(orders),
                "quotes": len(quotes),
            },
        }

    def submit_order(self, *args, **kwargs):
        raise PermissionError("BROKER_WRITE_DISABLED")

    def cancel_order(self, *args, **kwargs):
        raise PermissionError("BROKER_WRITE_DISABLED")
