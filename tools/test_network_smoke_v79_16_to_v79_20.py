import tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from alpaca_market_data import (
    NetworkSmokeConfig, inspect_network_smoke_preflight,
    build_bounded_stock_bars_request, execute_historical_network_smoke,
    sanitize_smoke_result, build_network_smoke_certificate,
)

class FakeResponse:
    data={"AAPL":[{"close":100}]}

class FakeClient:
    def __init__(self): self.calls=0
    def get_stock_bars(self, request):
        self.calls+=1
        return FakeResponse()

class Tests(unittest.TestCase):
    def setUp(self):
        self.config=NetworkSmokeConfig()
        self.now=datetime(2026,1,10,tzinfo=timezone.utc)
        self.good={
          "ALPACA_ENABLE_NETWORK_SMOKE":"YES",
          "APCA_API_KEY_ID":"TESTKEY_1234567890",
          "APCA_API_SECRET_KEY":"TESTSECRET_12345678901234567890",
        }

    def test_v79_16_default_is_not_authorized(self):
        p=inspect_network_smoke_preflight({})
        self.assertFalse(p.network_execution_authorized)

    def test_v79_16_exact_yes_required(self):
        env=dict(self.good); env["ALPACA_ENABLE_NETWORK_SMOKE"]="yes"
        self.assertFalse(inspect_network_smoke_preflight(env).network_execution_authorized)

    def test_v79_16_complete_opt_in(self):
        self.assertTrue(inspect_network_smoke_preflight(self.good).network_execution_authorized)

    def test_v79_17_bounded_request(self):
        request=build_bounded_stock_bars_request(self.config,now=self.now)
        self.assertEqual(request.limit,1)

    def test_v79_17_policy_rejects_larger_limit(self):
        with self.assertRaises(ValueError): NetworkSmokeConfig(limit=2).validate()

    def test_v79_18_safe_skip_without_credentials(self):
        result=execute_historical_network_smoke({},self.config,now=self.now)
        self.assertEqual(result.status,"SKIPPED_SAFE")
        self.assertEqual(result.network_request_count,0)

    def test_v79_18_one_request_with_approval(self):
        fake=FakeClient()
        result=execute_historical_network_smoke(
          self.good,self.config,client_factory=lambda k,s:fake,now=self.now)
        self.assertEqual(result.status,"PASS")
        self.assertEqual(result.network_request_count,1)
        self.assertEqual(fake.calls,1)

    def test_v79_18_error_is_redacted(self):
        class Bad:
            def get_stock_bars(self,request): raise RuntimeError("secret details")
        result=execute_historical_network_smoke(
          self.good,self.config,client_factory=lambda k,s:Bad(),now=self.now)
        self.assertEqual(result.status,"FAIL")
        self.assertNotIn("secret details",result.error_message_redacted)

    def test_v79_19_sanitizer(self):
        result=execute_historical_network_smoke({},self.config,now=self.now)
        doc=sanitize_smoke_result(result)
        self.assertFalse(doc["credentials_exposed"])
        self.assertFalse(doc["raw_response_persisted"])

    def test_trading_is_blocked(self):
        with self.assertRaises(ValueError):
            NetworkSmokeConfig(trading_api_allowed=True).validate()

    def test_v79_20_safe_skip_certificate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            p=root/"release/v79_15/output/authenticated_historical_gate_certificate_v79_15.json"
            p.parent.mkdir(parents=True); p.write_text('{"status":"PASS"}')
            pre=inspect_network_smoke_preflight({})
            result=execute_historical_network_smoke({},self.config,now=self.now)
            cert=build_network_smoke_certificate(
              root,root/"release/v79_20/output",self.config,pre,result,sanitize_smoke_result(result))
            self.assertEqual(cert["status"],"PASS")
            self.assertEqual(cert["network_smoke_mode"],"SKIPPED_SAFE")
            self.assertEqual(cert["actual_orders_submitted"],0)

    def test_no_trading_client_reference(self):
        text=(Path(__file__).resolve().parents[1]/"alpaca_market_data/network_smoke_v79_16_20.py").read_text()
        self.assertNotIn("TradingClient",text)
        self.assertNotIn("submit_order(",text)

if __name__=="__main__": unittest.main()
