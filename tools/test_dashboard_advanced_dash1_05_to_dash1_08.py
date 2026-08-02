import json,tempfile,unittest
from pathlib import Path
from dashboard.advanced_monitoring import performance_series,event_log,alerts,dashboard_health,build_advanced_payload
class Tests(unittest.TestCase):
 def w(self,root,rel,payload):
  p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(payload),encoding="utf-8")
 def root(self):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);return Path(td.name)
 def test_empty_performance_has_safe_point(self):
  self.assertEqual(len(performance_series(self.root())["equity"]),1)
 def test_equity_curve_maps(self):
  r=self.root();self.w(r,"release/op2_05_to_op2_08/actual/shadow_equity_curve.json",{"equity_curve":[{"trade_number":1,"cumulative_pnl":10,"drawdown":0}]})
  self.assertEqual(performance_series(r)["equity"][0]["y"],10)
 def test_runtime_event_maps(self):
  r=self.root();self.w(r,"release/op2_17_to_op2_20/actual/shadow_daily_automation_result.json",{"state":"WAIT_TEST","observed_at":"2026-01-01T00:00:00Z"})
  self.assertEqual(event_log(r)[0]["message"],"WAIT_TEST")
 def test_waiting_alerts(self):
  r=self.root();self.w(r,"release/op2_17_to_op2_20/actual/shadow_daily_automation_result.json",{"state":"WAIT_TEST"})
  codes={x["code"] for x in alerts(r)}
  self.assertIn("RUNTIME_WAITING",codes)
 def test_health_degraded_when_files_missing(self):
  self.assertEqual(dashboard_health(self.root())["dashboard_status"],"DEGRADED")
 def test_read_only_contract(self):
  p=build_advanced_payload(self.root())
  self.assertTrue(p["read_only"]);self.assertFalse(p["order_submission_enabled"]);self.assertFalse(p["broker_write_enabled"])
if __name__=="__main__":unittest.main()
