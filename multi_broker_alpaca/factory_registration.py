from __future__ import annotations
from multi_broker_core.factory import BrokerFactory
from .adapter import AlpacaReadOnlyAdapter
from .credentials import EnvironmentAlpacaCredentialProvider
from .transport import UrllibAlpacaReadOnlyTransport


def register_alpaca_adapter(factory: BrokerFactory) -> BrokerFactory:
    def builder(**kwargs):
        transport = kwargs.get("transport")
        if transport is None:
            provider = kwargs.get("credential_provider") or EnvironmentAlpacaCredentialProvider()
            credentials = provider.load()
            transport = UrllibAlpacaReadOnlyTransport(credentials)
        return AlpacaReadOnlyAdapter(transport=transport)

    factory.register("ALPACA", builder)
    return factory
