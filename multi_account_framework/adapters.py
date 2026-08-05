from __future__ import annotations


class BrokerAdapterContract:
    broker_name = "base"

    def capabilities(self) -> dict:
        return {
            "read_account": False,
            "read_positions": False,
            "read_orders": False,
            "submit_order": False,
            "cancel_order": False,
            "replace_order": False,
        }


class AlpacaAdapterContract(BrokerAdapterContract):
    broker_name = "alpaca"

    def capabilities(self) -> dict:
        return {
            "read_account": True,
            "read_positions": True,
            "read_orders": True,
            "submit_order": False,
            "cancel_order": False,
            "replace_order": False,
        }


class PlaceholderAdapterContract(BrokerAdapterContract):
    def __init__(self, broker_name: str) -> None:
        self.broker_name = broker_name


def adapter_for(broker: str) -> BrokerAdapterContract:
    if broker == "alpaca":
        return AlpacaAdapterContract()
    return PlaceholderAdapterContract(broker)
