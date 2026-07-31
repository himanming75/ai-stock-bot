import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from reporting.reporting_pipeline_v77_66_70 import *
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
  self.perf=self.r/"perf.json";self.risk=self.r/"risk.json";self.cert=self.r/"cert.json"
  write_json(self.perf,{"stage":"V77.61","status":"PASS","trade_count":2,"win_rate":0.5,"trade_pnl":25.0,
   "total_return":0.0025,"equity_before":10000.0,"equity_after":10025.0,
   "equity_curve":[{"sequence":0,"equity":10000.0,"event":"start"},{"sequence":1,"equity":10025.0,"event":"end"}]})
  write_json(self.risk,{"stage":"V77.63","status":"PASS","metrics":{"max_drawdown":0.0,"sharpe_ratio":0.0,
   "sortino_ratio":0.0,"profit_factor":2.0,"expectancy":12.5}})
  write_json(self.cert,{"stage":"V77.65","status":"PASS"})
 def tearDown(self):self.t.cleanup()
 def chain(self):
  o66=self.r/"o66";build_report_generator(self.perf,self.risk,self.cert,o66)
  o67=self.r/"o67";build_equity_curve_visualization(self.perf,o67)
  o68=self.r/"o68";build_trade_statistics_dashboard(o66/"performance_report_v77_66.json",self.risk,o68)
  o69=self.r/"o69";run_reporting_safety_gate(o66/"performance_report_v77_66.json",
    o67/"equity_curve_visualization_v77_67.json",o68/"trade_statistics_dashboard_v77_68.json",o69)
  return issue_reporting_certificate(o66/"performance_report_verification_v77_66.json",
   o67/"equity_curve_visualization_verification_v77_67.json",
   o68/"trade_statistics_dashboard_verification_v77_68.json",
   o69/"reporting_safety_gate_verification_v77_69.json",self.r/"o70")
 def test_full_chain(self):self.assertEqual(self.chain()["status"],"PASS")
 def test_report_files(self):
  o=self.r/"o";build_report_generator(self.perf,self.risk,self.cert,o);self.assertTrue((o/"performance_report_v77_66.md").is_file())
 def test_equity_files(self):
  o=self.r/"o";d=build_equity_curve_visualization(self.perf,o);self.assertEqual(d["point_count"],2);self.assertTrue((o/"equity_curve_v77_67.svg").is_file())
 def test_dashboard_cards(self):
  o=self.r/"o";build_report_generator(self.perf,self.risk,self.cert,o)
  d=build_trade_statistics_dashboard(o/"performance_report_v77_66.json",self.risk,self.r/"o68");self.assertGreaterEqual(len(d["cards"]),6)
 def test_invalid_curve_blocked(self):
  write_json(self.perf,{"stage":"V77.61","status":"PASS","equity_curve":[{"sequence":0,"equity":100.0}]})
  self.assertEqual(build_equity_curve_visualization(self.perf,self.r/"o")["status"],"FAIL")
 def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
