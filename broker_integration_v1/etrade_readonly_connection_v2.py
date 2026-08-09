from __future__ import annotations

from .etrade_profile import ETRADE_API_PROFILE
from .etrade_readonly_adapter import ETradeReadOnlyAdapter
from .etrade_network_transport_v2 import ETradeOAuthReadOnlyTransport


def environment_base_url(environment):
    env=str(environment).lower()
    if env=="sandbox":
        return ETRADE_API_PROFILE["sandbox_base_url"]
    if env=="production":
        return ETRADE_API_PROFILE["production_base_url"]
    raise ValueError("environment must be sandbox or production")


class ETradeReadOnlyConnection:
    def __init__(self,consumer_key,consumer_secret,access_token,access_token_secret,environment="sandbox",network_enabled=False):
        transport=ETradeOAuthReadOnlyTransport(
            consumer_key,consumer_secret,access_token,access_token_secret,
            environment_base_url(environment),network_enabled=network_enabled,
        )
        self.environment=environment
        self.transport=transport
        self.adapter=ETradeReadOnlyAdapter(transport)

    def list_accounts(self):
        payload=self.adapter.list_accounts_raw()
        response=payload.get("AccountListResponse") or payload
        accounts=response.get("Accounts") or response.get("accounts") or {}
        rows=accounts.get("Account") or accounts.get("account") or []
        return rows if isinstance(rows,list) else [rows]

    def snapshot(self,account_id_key):
        return self.adapter.get_account_snapshot_from_fixture(account_id_key)

    def submit_order(self,*args,**kwargs):
        raise PermissionError("Broker Integration V2 remains read-only.")

    def cancel_order(self,*args,**kwargs):
        raise PermissionError("Broker Integration V2 remains read-only.")
