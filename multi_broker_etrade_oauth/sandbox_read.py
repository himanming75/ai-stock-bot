from __future__ import annotations
from multi_broker_core.factory import BrokerFactory
from multi_broker_etrade.credentials import ETradeOAuthCredentials
from multi_broker_etrade.factory_registration import register_etrade_adapter
from multi_broker_etrade.transport import UrllibETradeOAuthTransport


def build_sandbox_adapter(
    *,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_secret: str,
    account_id_key: str | None = None,
):
    credentials = ETradeOAuthCredentials(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_secret=access_secret,
        environment="SANDBOX",
    )
    factory = register_etrade_adapter(BrokerFactory())
    return factory.create(
        "ETRADE",
        transport=UrllibETradeOAuthTransport(credentials),
        account_id_key=account_id_key,
    )
