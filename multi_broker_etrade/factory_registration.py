from __future__ import annotations
from multi_broker_core.factory import BrokerFactory
from .adapter import ETradeReadOnlyAdapter
from .credentials import EnvironmentETradeCredentialProvider
from .transport import UrllibETradeOAuthTransport


def register_etrade_adapter(factory: BrokerFactory) -> BrokerFactory:
    def builder(**kwargs):
        transport = kwargs.get("transport")
        if transport is None:
            provider = (
                kwargs.get("credential_provider")
                or EnvironmentETradeCredentialProvider()
            )
            credentials = provider.load()
            transport = UrllibETradeOAuthTransport(credentials)
        return ETradeReadOnlyAdapter(
            transport=transport,
            account_id_key=kwargs.get("account_id_key"),
        )

    factory.register("ETRADE", builder)
    return factory
