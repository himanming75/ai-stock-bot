import math,tempfile,unittest
from pathlib import Path
from performance_accounting.performance_accounting_pipeline_v78_71_75 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"

        write_json(self.cert,{
            "stage":"V78.70","status":"PASS",
            "certification_scope":"OFFLINE_PERFORMANCE_ACCOUNTING_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"}
        })
        write_json(self.cfg,{
            "performance_accounting":{
                "starting_equity":100000.0,
                "labels":["P1","P2","P3","P4"],
                "equity_values":[100100.0,99900.0,100200.0,100150.0],
                "trade_pnls":[100.0,-200.0,300.0,-50.0],
                "annualization_factor":252.0
            }
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o71=self.r/"o71"
        a=build_performance_accounting_foundation(self.cert,self.cfg,o71)
        o72=self.r/"o72"
        b=run_equity_curve_return_ledger(
            o71/"performance_accounting_foundation_v78_71.json",o72)
        o73=self.r/"o73"
        c=run_performance_metrics_engine(
            o71/"performance_accounting_foundation_v78_71.json",
            o72/"equity_curve_return_ledger_v78_72.json",o73)
        o74=self.r/"o74"
        d=run_performance_accounting_safety_gate(
            o71/"performance_accounting_foundation_v78_71.json",
            o72/"equity_curve_return_ledger_v78_72.json",
            o73/"performance_metrics_engine_v78_73.json",o74)
        o75=self.r/"o75"
        e=issue_performance_accounting_certificate(
            o71/"performance_accounting_foundation_verification_v78_71.json",
            o72/"equity_curve_return_ledger_verification_v78_72.json",
            o73/"performance_metrics_engine_verification_v78_73.json",
            o74/"performance_accounting_safety_gate_verification_v78_74.json",
            o71/"performance_accounting_foundation_v78_71.json",o75)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_equity_curve_values(self):
        points=build_equity_curve(100.0,[110.0,99.0],["a","b"])
        self.assertEqual(points[0].period_return,0.1)
        self.assertEqual(points[1].cumulative_return,-0.01)
        self.assertEqual(points[1].drawdown,-0.1)

    def test_invalid_equity_blocked(self):
        with self.assertRaises(ValueError):
            build_equity_curve(100.0,[0.0],["a"])

    def test_metric_counts(self):
        points=build_equity_curve(100.0,[101.0,102.0],["a","b"])
        m=calculate_performance_metrics(points,[10,-5,0],252)
        self.assertEqual(m["trade_count"],3)
        self.assertEqual(m["win_count"],1)
        self.assertEqual(m["loss_count"],1)
        self.assertEqual(m["flat_count"],1)

    def test_profit_factor(self):
        points=build_equity_curve(100.0,[101.0],["a"])
        m=calculate_performance_metrics(points,[10,-5],252)
        self.assertEqual(m["profit_factor"],2.0)

    def test_zero_volatility_sharpe(self):
        points=build_equity_curve(100.0,[100.0,100.0],["a","b"])
        m=calculate_performance_metrics(points,[],252)
        self.assertEqual(m["sharpe_ratio"],0.0)

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_REPORTING_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.70","status":"FAIL"})
        self.assertEqual(
            build_performance_accounting_foundation(self.cert,self.cfg,self.r/"bad")["status"],
            "FAIL"
        )

    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"])
            self.assertFalse(x["broker_connected"])

    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))

if __name__=="__main__":
    unittest.main()
