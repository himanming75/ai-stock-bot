from pathlib import Path
from tempfile import TemporaryDirectory
import math, unittest
from alpaca_market_data.paper_performance_analytics_v81_81_v82_00 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperPerformanceConfig();self.f=performance_fixture(self.c.initial_equity)
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperPerformanceConfig(allow_network=True).validate()
 def test_fixture(self): self.assertEqual(self.f["observation_count"],10)
 def test_validate_fixture(self): validate_fixture(self.f,self.c)
 def test_bad_fixture(self):
  bad=dict(self.f);bad["period_returns"]=[1]
  with self.assertRaises(ValueError):validate_fixture(bad,self.c)
 def test_returns(self): self.assertGreater(return_metrics(self.f,self.c)["ending_equity"],0)
 def test_drawdown(self): self.assertGreaterEqual(drawdown_metrics(self.f)["max_drawdown_pct"],0)
 def test_risk_adjusted(self):
  r=risk_adjusted_metrics(self.f,self.c);self.assertTrue(math.isfinite(r["sharpe_ratio"]))
 def test_trade_metrics(self): self.assertEqual(trade_metrics(self.f)["trade_count"],6)
 def test_profit_factor(self): self.assertGreater(trade_metrics(self.f)["profit_factor"],0)
 def test_calmar(self):
  self.assertTrue(math.isfinite(calmar_ratio(return_metrics(self.f,self.c),drawdown_metrics(self.f))["calmar_ratio"]))
 def test_reports(self):
  r=time_bucket_reports(self.f);self.assertEqual(len(r["daily"]),10)
 def test_risk_gate(self): self.assertEqual(risk_gate(drawdown_metrics(self.f),self.c)["status"],"PASS")
 def test_scorecard(self):
  rd=return_metrics(self.f,self.c);dd=drawdown_metrics(self.f);ra=risk_adjusted_metrics(self.f,self.c);tm=trade_metrics(self.f)
  self.assertEqual(build_scorecard(rd,dd,ra,tm,calmar_ratio(rd,dd),risk_gate(dd,self.c))["status"],"PASS")
 def test_audit(self):
  rd=return_metrics(self.f,self.c);dd=drawdown_metrics(self.f);ra=risk_adjusted_metrics(self.f,self.c);tm=trade_metrics(self.f);rp=time_bucket_reports(self.f)
  sc=build_scorecard(rd,dd,ra,tm,calmar_ratio(rd,dd),risk_gate(dd,self.c))
  self.assertEqual(build_audit(self.f,rd,dd,ra,tm,rp,sc)["status"],"PASS")
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);store_package(out,{"a":{"x":1}});self.assertTrue(store_package(out,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);(out/"packages"/z["package_id"]/"a.json").write_text("{}")
   with self.assertRaises(ValueError):verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_execution_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_performance_analytics_v81_81_v82_00.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V81.{i:02d}" for i in range(81,100)]+["V82.00"]),20)
if __name__=="__main__":unittest.main()
