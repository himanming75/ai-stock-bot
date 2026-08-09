from pathlib import Path
import ast
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker.contracts_v77_1 import (
    AccountSnapshot,
    BrokerCapabilities,
    BrokerEnvironment,
)
from broker_integration_v1.contract_reuse import (
    AccountSnapshot as ReusedAccountSnapshot,
    BrokerCapabilities as ReusedBrokerCapabilities,
    contract_reuse_certificate,
)
from broker_integration_v1.credential_isolation import (
    redact_mapping,
    credential_isolation_certificate,
)
from broker_integration_v1.etrade_profile import (
    ETRADE_API_PROFILE,
    etrade_profile_certificate,
)
from broker_integration_v1.etrade_readonly_adapter import (
    ETradeReadOnlyAdapter,
)
from broker_integration_v1.transport import (
    FixtureTransport,
    NoNetworkTransport,
    NetworkDisabledError,
)
from broker_integration_v1.normalization import (
    normalize_etrade_account,
)
from broker_integration_v1.alpaca_existing_bridge import (
    alpaca_reuse_certificate,
)
from broker_integration_v1.broker_registry import (
    build_broker_registry,
)
from broker_integration_v1.live_safety_gateway import (
    build_live_safety_gateway,
    assert_read_only,
)
from broker_integration_v1.integrated_status import (
    build_broker_integration_v1_status,
)

class TestBrokerIntegrationV1(unittest.TestCase):
    def test_reuses_canonical_contract_identity(self):
        self.assertIs(AccountSnapshot, ReusedAccountSnapshot)
        self.assertIs(BrokerCapabilities, ReusedBrokerCapabilities)
        cert=contract_reuse_certificate()
        self.assertEqual(cert["canonical_contract_module"],"broker.contracts_v77_1")
        self.assertFalse(cert["duplicate_contracts_created"])

    def test_no_duplicate_core_contract_classes_declared(self):
        forbidden={
            "AccountSnapshot","BrokerCapabilities","BrokerContract",
            "BrokerOrder","BrokerOrderRequest","BrokerPosition",
            "BrokerSafetyPolicy",
        }
        violations=[]
        for path in (ROOT/"broker_integration_v1").glob("*.py"):
            tree=ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node,ast.ClassDef) and node.name in forbidden:
                    violations.append(f"{path.name}:{node.name}")
        self.assertEqual(violations,[])

    def test_default_etrade_transport_forbids_network(self):
        adapter=ETradeReadOnlyAdapter()
        self.assertIsInstance(adapter.transport,NoNetworkTransport)
        with self.assertRaises(NetworkDisabledError):
            adapter.list_accounts_raw()

    def test_etrade_submit_cancel_locked(self):
        adapter=ETradeReadOnlyAdapter()
        with self.assertRaises(PermissionError):
            adapter.submit_order(None)
        with self.assertRaises(PermissionError):
            adapter.cancel_order("X")

    def test_etrade_fixture_normalizes_to_canonical_account_snapshot(self):
        snap=normalize_etrade_account(
            "123456789",
            {
                "BalanceResponse":{
                    "Computed":{
                        "cashAvailableForInvestment":"1000.50",
                        "marginBuyingPower":"2000.00",
                        "RealTimeValues":{"totalAccountValue":"2500.75"},
                    }
                }
            },
            {
                "PortfolioResponse":{
                    "AccountPortfolio":[{
                        "Position":[{
                            "Product":{"symbol":"AAPL"},
                            "quantity":"2",
                            "pricePaid":"100",
                            "marketValue":"220",
                            "totalGain":"20",
                        }]
                    }]
                }
            },
            {"OrdersResponse":{"Order":[]}},
        )
        self.assertIsInstance(snap,AccountSnapshot)
        self.assertEqual(snap.account_id_masked,"*****6789")
        self.assertEqual(len(snap.positions),1)
        self.assertEqual(snap.positions[0].symbol,"AAPL")
        snap.validate()

    def test_etrade_fixture_transport_readonly_adapter(self):
        aid="ABC123"
        balance_path=f"/accounts/{aid}/balance.json"
        portfolio_path=f"/accounts/{aid}/portfolio.json"
        orders_path=f"/accounts/{aid}/orders.json"
        t=FixtureTransport({
            balance_path:{"BalanceResponse":{"Computed":{
                "cashAvailableForInvestment":"100",
                "marginBuyingPower":"100",
                "RealTimeValues":{"totalAccountValue":"100"},
            }}},
            portfolio_path:{"PortfolioResponse":{"AccountPortfolio":[]}},
            orders_path:{"OrdersResponse":{"Order":[]}},
        })
        a=ETradeReadOnlyAdapter(t)
        snap=a.get_account_snapshot_from_fixture(aid)
        self.assertIsInstance(snap,AccountSnapshot)
        self.assertEqual(len(t.calls),3)

    def test_capabilities_are_offline_and_readonly(self):
        c=ETradeReadOnlyAdapter().capabilities
        self.assertEqual(c.environment,BrokerEnvironment.OFFLINE)
        self.assertFalse(c.supports_market_orders)
        self.assertFalse(c.supports_cancel)
        self.assertFalse(c.supports_replace)
        c.validate()

    def test_credentials_redacted_and_not_read(self):
        redacted=redact_mapping({
            "consumer_key":"visible-id",
            "consumer_secret":"abc",
            "access_token":"xyz",
        })
        self.assertEqual(redacted["consumer_secret"],"***REDACTED***")
        self.assertEqual(redacted["access_token"],"***REDACTED***")
        cert=credential_isolation_certificate()
        self.assertFalse(cert["credential_values_read"])
        self.assertFalse(cert["credential_values_logged"])

    def test_etrade_profile_oauth_and_readonly(self):
        self.assertEqual(ETRADE_API_PROFILE["auth_protocol"],"OAuth 1.0a")
        self.assertEqual(ETRADE_API_PROFILE["signature_method"],"HMAC-SHA1")
        self.assertFalse(ETRADE_API_PROFILE["write_endpoints_enabled"])
        self.assertFalse(ETRADE_API_PROFILE["network_enabled_by_default"])
        self.assertTrue(etrade_profile_certificate()["read_only"])

    def test_alpaca_stack_is_reused(self):
        cert=alpaca_reuse_certificate()
        self.assertTrue(cert["existing_alpaca_market_data_stack_reused"])
        self.assertFalse(cert["new_alpaca_market_data_client_created"])

    def test_registry_reports_no_duplicates(self):
        r=build_broker_registry()
        self.assertFalse(r["duplicate_broker_contract_created"])
        self.assertFalse(r["duplicate_alpaca_market_data_stack_created"])
        self.assertEqual(r["etrade_adapter_mode"],"READ_ONLY_FOUNDATION")

    def test_safety_gateway_locked(self):
        g=build_live_safety_gateway()
        self.assertTrue(g["broker_write_locked"])
        self.assertTrue(g["order_submission_locked"])
        self.assertTrue(g["cancel_replace_locked"])
        self.assertTrue(g["live_trading_locked"])
        self.assertFalse(g["unlock_supported_in_v1"])
        self.assertTrue(assert_read_only())

    def test_integrated_status_locked(self):
        s=build_broker_integration_v1_status()
        self.assertEqual(s["development_status"],"COMPLETE")
        self.assertEqual(s["network_status"],"LOCKED")
        self.assertEqual(s["live_trading_status"],"LOCKED")
        self.assertFalse(s["contracts"]["duplicate_broker_contract_created"])
        self.assertFalse(s["contracts"]["broker_network_used"])
        self.assertFalse(s["contracts"]["order_submission_performed"])

if __name__=="__main__":
    unittest.main()
