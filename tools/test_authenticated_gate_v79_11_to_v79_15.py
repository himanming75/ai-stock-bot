import tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from alpaca_market_data import (
    AuthenticatedClientPolicy, inspect_credentials, issue_network_approval,
    build_authenticated_client, authorize_historical_request,
    build_authenticated_gate_certificate,
)
class Tests(unittest.TestCase):
    def setUp(self):
        self.source={"APCA_API_KEY_ID":"TESTKEY_1234567890","APCA_API_SECRET_KEY":"TESTSECRET_12345678901234567890"}
        self.now=datetime(2026,1,1,tzinfo=timezone.utc)
    def test_v79_11_complete_pair(self):
        x=inspect_credentials(self.source); self.assertTrue(x.ready_for_client_creation); self.assertFalse(x.values_exposed)
    def test_v79_11_missing_secret(self):
        x=inspect_credentials({"APCA_API_KEY_ID":"TESTKEY_1234567890"}); self.assertFalse(x.pair_complete)
    def test_v79_11_bad_shape(self):
        self.assertFalse(inspect_credentials({"APCA_API_KEY_ID":"bad key","APCA_API_SECRET_KEY":"short"}).ready_for_client_creation)
    def test_v79_12_approval_valid(self):
        a=issue_network_approval(approved=True,now=self.now,token_id="fixed"); a.validate(self.now)
    def test_v79_12_denied(self):
        a=issue_network_approval(approved=False,now=self.now,token_id="fixed")
        with self.assertRaises(PermissionError): a.validate(self.now)
    def test_v79_12_expired(self):
        a=issue_network_approval(approved=True,ttl_minutes=1,now=self.now,token_id="fixed")
        with self.assertRaises(PermissionError): a.validate(datetime(2026,1,1,0,2,tzinfo=timezone.utc))
    def test_v79_13_client_created_without_request(self):
        x=inspect_credentials(self.source); r=build_authenticated_client(self.source,x,AuthenticatedClientPolicy())
        self.assertEqual(r.metadata["client_type"],"StockHistoricalDataClient"); self.assertFalse(r.metadata["network_request_performed"])
    def test_v79_13_rejects_bad_credentials(self):
        with self.assertRaises(PermissionError):
            build_authenticated_client({},inspect_credentials({}),AuthenticatedClientPolicy())
    def test_v79_14_only_stock_bars(self):
        a=issue_network_approval(approved=True,now=self.now,token_id="fixed")
        r=authorize_historical_request(a,AuthenticatedClientPolicy(),requested_operation="GET_STOCK_BARS",now=self.now)
        self.assertTrue(r["authorized"]); self.assertFalse(r["network_request_executed"])
    def test_v79_14_rejects_orders(self):
        a=issue_network_approval(approved=True,now=self.now,token_id="fixed")
        with self.assertRaises(PermissionError):
            authorize_historical_request(a,AuthenticatedClientPolicy(),requested_operation="SUBMIT_ORDER",now=self.now)
    def test_policy_blocks_trading(self):
        with self.assertRaises(ValueError): AuthenticatedClientPolicy(trading_client_allowed=True).validate()
    def test_v79_15_certificate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); p=root/"release/v79_10/output/alpaca_historical_data_certificate_v79_10.json"; p.parent.mkdir(parents=True); p.write_text('{"status":"PASS"}')
            x=inspect_credentials(self.source); pol=AuthenticatedClientPolicy()
            a=issue_network_approval(approved=True,now=self.now,token_id="fixed")
            c=build_authenticated_client(self.source,x,pol)
            auth=authorize_historical_request(a,pol,requested_operation="GET_STOCK_BARS",now=self.now)
            cert=build_authenticated_gate_certificate(root,root/"release/v79_15/output",x,a,pol,c.metadata,auth)
            self.assertEqual(cert["status"],"PASS"); self.assertEqual(cert["actual_orders_submitted"],0)
if __name__=="__main__": unittest.main()
