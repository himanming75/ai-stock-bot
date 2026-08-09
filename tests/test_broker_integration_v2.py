from pathlib import Path
import ast
import os
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_oauth_signer import official_signature_test_vector
from broker_integration_v1.etrade_oauth_flow_v2 import ETradeOAuthFlow, OAuthNetworkDisabled
from broker_integration_v1.etrade_network_transport_v2 import ETradeOAuthReadOnlyTransport, ReadOnlyNetworkPolicyError
from broker_integration_v1.integrated_status_v2 import build_broker_integration_v2_status
from broker_integration_v1.etrade_readonly_connection_v2 import environment_base_url


class TestBrokerIntegrationV2(unittest.TestCase):
    def test_official_signature_vector(self):
        self.assertTrue(official_signature_test_vector()["matches"])

    def test_oauth_network_default_locked(self):
        f=ETradeOAuthFlow("key","secret",network_enabled=False)
        with self.assertRaises(OAuthNetworkDisabled):
            f.request_token()

    def test_readonly_transport_network_default_locked(self):
        t=ETradeOAuthReadOnlyTransport("k","s","t","ts","https://apisb.etrade.com/v1")
        with self.assertRaises(ReadOnlyNetworkPolicyError):
            t.get_json("/accounts/list.json")

    def test_readonly_transport_blocks_post_semantics(self):
        t=ETradeOAuthReadOnlyTransport("k","s","t","ts","https://apisb.etrade.com/v1",network_enabled=True)
        with self.assertRaises(ReadOnlyNetworkPolicyError):
            t._assert_readonly("POST","/accounts/x/orders")

    def test_readonly_transport_blocks_nonaccount_path(self):
        t=ETradeOAuthReadOnlyTransport("k","s","t","ts","https://apisb.etrade.com/v1",network_enabled=True)
        with self.assertRaises(ReadOnlyNetworkPolicyError):
            t._assert_readonly("GET","/market/quote/AAPL")

    def test_environment_urls(self):
        self.assertEqual(environment_base_url("sandbox"),"https://apisb.etrade.com/v1")
        self.assertEqual(environment_base_url("production"),"https://api.etrade.com/v1")

    def test_status_without_credentials_waits(self):
        oldk=os.environ.pop("ETRADE_CONSUMER_KEY",None)
        olds=os.environ.pop("ETRADE_CONSUMER_SECRET",None)
        try:
            s=build_broker_integration_v2_status(ROOT)
            self.assertEqual(s["development_status"],"COMPLETE")
            self.assertEqual(s["etrade_oauth_status"],"WAITING_FOR_CREDENTIALS")
            self.assertEqual(s["token_persistence"],"DISABLED")
        finally:
            if oldk is not None: os.environ["ETRADE_CONSUMER_KEY"]=oldk
            if olds is not None: os.environ["ETRADE_CONSUMER_SECRET"]=olds

    def test_status_with_credentials_ready(self):
        oldk=os.environ.get("ETRADE_CONSUMER_KEY")
        olds=os.environ.get("ETRADE_CONSUMER_SECRET")
        os.environ["ETRADE_CONSUMER_KEY"]="dummy"
        os.environ["ETRADE_CONSUMER_SECRET"]="dummy"
        try:
            s=build_broker_integration_v2_status(ROOT)
            self.assertEqual(s["etrade_oauth_status"],"READY_FOR_USER_AUTHORIZED_READONLY_CONNECTION")
        finally:
            if oldk is None: os.environ.pop("ETRADE_CONSUMER_KEY",None)
            else: os.environ["ETRADE_CONSUMER_KEY"]=oldk
            if olds is None: os.environ.pop("ETRADE_CONSUMER_SECRET",None)
            else: os.environ["ETRADE_CONSUMER_SECRET"]=olds

    def test_no_duplicate_adapter_class(self):
        forbidden={"ETradeReadOnlyAdapter","AccountSnapshot","BrokerContract","BrokerPosition"}
        bad=[]
        for p in [
            ROOT/"broker_integration_v1"/"etrade_oauth_signer.py",
            ROOT/"broker_integration_v1"/"etrade_oauth_flow_v2.py",
            ROOT/"broker_integration_v1"/"etrade_network_transport_v2.py",
            ROOT/"broker_integration_v1"/"etrade_readonly_connection_v2.py",
            ROOT/"broker_integration_v1"/"integrated_status_v2.py",
        ]:
            tree=ast.parse(p.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node,ast.ClassDef) and node.name in forbidden:
                    bad.append(node.name)
        self.assertEqual(bad,[])

    def test_safety_contracts(self):
        s=build_broker_integration_v2_status(ROOT)
        c=s["contracts"]
        self.assertTrue(c["v1_bridge_reused"])
        self.assertTrue(c["canonical_v77_1_contract_reused"])
        self.assertTrue(c["existing_etrade_v1_adapter_reused"])
        self.assertFalse(c["duplicate_broker_contract_created"])
        self.assertFalse(c["duplicate_etrade_readonly_adapter_created"])
        self.assertFalse(c["new_credential_vault_created"])
        self.assertFalse(c["access_token_persisted"])
        self.assertFalse(c["broker_write_performed"])
        self.assertFalse(c["order_submission_performed"])
        self.assertFalse(c["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
