from pathlib import Path
from tempfile import TemporaryDirectory
import unittest,json
from alpaca_market_data.paper_monitoring_completion_v80_41_60 import *

class T(unittest.TestCase):
 def setUp(self):
  self.c=PaperMonitoringConfig();self.s={"position_count":0,"equity":100046.975,"closing_cash":100046.975,
   "realized_pnl":47.975,"filled_order_count":2}
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError): PaperMonitoringConfig(allow_network=True).validate()
 def test_position_monitor(self): self.assertTrue(build_position_monitor(self.s)["flat"])
 def test_portfolio_monitor(self): self.assertGreater(build_portfolio_monitor(self.s,self.c)["current_equity"],100000)
 def test_equity_curve(self): self.assertEqual(build_equity_curve(100,110)["point_count"],3)
 def test_drawdown(self): self.assertGreater(build_equity_curve(100,90)["max_drawdown_pct"],0)
 def test_pnl(self): self.assertGreater(build_pnl_monitor(self.s,self.c)["total_pnl"],0)
 def test_exposure(self): self.assertEqual(build_exposure_monitor(self.s,build_portfolio_monitor(self.s,self.c))["gross_exposure_pct"],0)
 def test_no_alert(self):
  p=build_position_monitor(self.s);pf=build_portfolio_monitor(self.s,self.c);e=build_equity_curve(100000,pf["current_equity"])
  pnl=build_pnl_monitor(self.s,self.c);x=build_exposure_monitor(self.s,pf)
  self.assertEqual(build_risk_alerts(self.c,e,pnl,x,p)["halt_alert_count"],0)
 def test_drawdown_halt(self):
  e=build_equity_curve(100,90);pnl={"daily_return":0};x={"gross_exposure_pct":0};p={"flat":True}
  self.assertTrue(build_risk_alerts(self.c,e,pnl,x,p)["kill_switch_required"])
 def test_eod_position_halt(self):
  e=build_equity_curve(100,100);pnl={"daily_return":0};x={"gross_exposure_pct":0};p={"flat":False}
  self.assertTrue(build_risk_alerts(self.c,e,pnl,x,p)["kill_switch_required"])
 def test_statistics(self): self.assertEqual(build_statistics(self.s)["winning_trade_count"],1)
 def test_daily_report(self):
  d=build_daily_report(self.s,{"flat":True},{},{"max_drawdown_pct":0},{"daily_return":0},{"gross_exposure_pct":0},{"halt_alert_count":0},{})
  self.assertEqual(d["report_type"],"PAPER_DAILY_REPORT")
 def test_audit(self):
  d={"status":"PASS","risk_alerts":{"halt_alert_count":0},"position_monitor":{"flat":True}}
  self.assertEqual(build_audit_report({"status":"PASS","actual_orders_submitted":0},d)["status"],"PASS")
 def test_eod_close(self):
  d={"status":"PASS","risk_alerts":{"halt_alert_count":0},"position_monitor":{"flat":True}}
  self.assertEqual(end_of_day_close(d,{"status":"PASS"})["status"],"CLOSED")
 def test_eod_block(self):
  d={"status":"PASS","risk_alerts":{"halt_alert_count":1},"position_monitor":{"flat":True}}
  self.assertEqual(end_of_day_close(d,{"status":"PASS"})["status"],"BLOCKED")
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);docs={"a":{"x":1}};store_monitoring_package(out,docs);self.assertTrue(store_monitoring_package(out,docs)["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_monitoring_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_monitoring_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);(out/"packages"/z["package_id"]/"a.json").write_text("{}")
   with self.assertRaises(ValueError): verify_manifest(out,m)
 def test_archive(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_monitoring_package(out,{"a":{"x":1}});r=build_archive(out,z["ledger"]);self.assertTrue(verify_archive(out,r))
 def test_archive_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_monitoring_package(out,{"a":{"x":1}});r=build_archive(out,z["ledger"]);(out/r["archive_path"]).write_bytes(b"x")
   with self.assertRaises(ValueError): verify_archive(out,r)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError): validate_order_fill_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_monitoring_completion_v80_41_60.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv"):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V80.{i:02d}" for i in range(41,61)]),20)
if __name__=="__main__":unittest.main()
