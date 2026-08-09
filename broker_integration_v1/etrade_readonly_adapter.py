from datetime import datetime, timezone

from broker.contracts_v77_1 import (
    BrokerCapabilities,
    BrokerEnvironment,
    BrokerHealth,
    TimeInForce,
)
from .etrade_profile import ETRADE_API_PROFILE
from .normalization import normalize_etrade_account
from .transport import NoNetworkTransport

class ETradeReadOnlyAdapter:
    def __init__(self, transport=None):
        self.transport=transport or NoNetworkTransport()

    @property
    def capabilities(self):
        return BrokerCapabilities(
            supports_market_orders=False,
            supports_limit_orders=False,
            supports_stop_orders=False,
            supports_stop_limit_orders=False,
            supports_fractional_quantity=False,
            supports_cancel=False,
            supports_replace=False,
            supported_time_in_force=(TimeInForce.DAY,),
            environment=BrokerEnvironment.OFFLINE,
        )

    def health(self):
        return BrokerHealth(
            environment=BrokerEnvironment.OFFLINE,
            adapter_name="ETradeReadOnlyAdapterV1",
            connected=False,
            authenticated=False,
            network_used=False,
            checked_at_utc=datetime.now(timezone.utc),
            details={"mode":"READ_ONLY_FOUNDATION","oauth":"1.0a"},
        )

    def list_accounts_raw(self):
        return self.transport.get_json(ETRADE_API_PROFILE["read_endpoints"]["accounts"])

    def get_account_snapshot_from_fixture(self, account_id_key):
        balance_path=ETRADE_API_PROFILE["read_endpoints"]["balance"].format(accountIdKey=account_id_key)
        portfolio_path=ETRADE_API_PROFILE["read_endpoints"]["portfolio"].format(accountIdKey=account_id_key)
        orders_path=ETRADE_API_PROFILE["read_endpoints"]["orders"].format(accountIdKey=account_id_key)
        balance=self.transport.get_json(balance_path)
        portfolio=self.transport.get_json(portfolio_path)
        orders=self.transport.get_json(orders_path)
        return normalize_etrade_account(account_id_key,balance,portfolio,orders)

    def submit_order(self, request):
        raise PermissionError("E*TRADE order submission is locked in Broker Integration V1.")

    def cancel_order(self, broker_order_id):
        raise PermissionError("E*TRADE order cancellation is locked in Broker Integration V1.")
