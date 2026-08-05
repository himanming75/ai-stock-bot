import json,tempfile,unittest
from pathlib import Path
from dashboard.paper_trading_integration import build_paper_trading_payload
class Tests(unittest.TestCase):
 def w(self,r,rel,v):p=r/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf-8")
 def root(self):td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);return Path(td.name)
 def test_missing_data_safe(self):
  p=build_paper_trading_payload(self.root());self.assertTrue(p["read_only"]);self.assertEqual(p["account"]["status"],"NOT_AVAILABLE")
 def test_account_maps(self):
  r=self.root();self.w(r,"release/op3_13_to_op3_16/input/limited_autonomous_account_snapshot.json",{"account":{"status":"ACTIVE","cash":"100","buying_power":"200","portfolio_value":"110","equity":"110"}})
  p=build_paper_trading_payload(r);self.assertEqual(p["account"]["cash"],100)
 def test_lifecycle_maps(self):
  r=self.root();self.w(r,"release/op3_09_to_op3_12/actual/paper_order_lifecycle_result.json",{"broker_order_id":"1","symbol":"AAPL","order_status":"accepted","fill_state":"NOT_FILLED","recovery_required":True})
  p=build_paper_trading_payload(r);self.assertEqual(p["order_lifecycle"]["status"],"accepted")
 def test_positions_map(self):
  r=self.root();self.w(r,"release/op3_09_to_op3_12/input/local_paper_positions_snapshot.json",{"positions":[{"symbol":"AAPL","qty":"1"}]})
  p=build_paper_trading_payload(r);self.assertEqual(len(p["positions"]),1)
 def test_risk_maps(self):
  r=self.root();self.w(r,"release/op3_13_to_op3_16/input/limited_autonomous_risk_snapshot.json",{"daily_orders":1,"market_open":False,"emergency_stop_engaged":True})
  p=build_paper_trading_payload(r);self.assertTrue(p["risk"]["emergency_stop_engaged"])
 def test_no_order_controls(self):
  p=build_paper_trading_payload(self.root());self.assertFalse(p["order_controls_available"]);self.assertFalse(p["broker_write_enabled"])
if __name__=="__main__":unittest.main()
