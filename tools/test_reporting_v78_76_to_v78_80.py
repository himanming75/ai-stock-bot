import json,tempfile,unittest
from pathlib import Path
from reporting.reporting_pipeline_v78_76_80 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        self.metrics=self.r/"metrics.json"
        self.equity=self.r/"equity.json"

        write_json(self.cert,{
            "stage":"V78.75","status":"PASS",
            "certification_scope":"OFFLINE_REPORTING_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"}
        })
        write_json(self.cfg,{
            "reporting":{
                "report_id":"RID","report_version":"1.0","title":"Test Report",
                "required_sections":["summary","trade_statistics","equity_curve","safety"],
                "export_formats":["json","csv","markdown"]
            }
        })
        write_json(self.metrics,{
            "stage":"V78.73","status":"PASS",
            "performance_metrics":{
                "ending_equity":101000.0,"cumulative_return":0.01,"max_drawdown":-0.02,
                "mean_period_return":0.001,"return_volatility":0.01,"sharpe_ratio":1.2,
                "trade_count":2,"win_count":1,"loss_count":1,"flat_count":0,
                "win_rate":0.5,"gross_profit":200.0,"gross_loss":100.0,
                "profit_factor":2.0,"expectancy":50.0,"average_win":200.0,"average_loss":-100.0
            }
        })
        curve=[
            {"sequence":1,"label":"P1","equity":100500.0,"period_return":0.005,
             "cumulative_return":0.005,"drawdown":0.0,"equity_sha256":"e1"},
            {"sequence":2,"label":"P2","equity":101000.0,"period_return":0.004975124378,
             "cumulative_return":0.01,"drawdown":0.0,"equity_sha256":"e2"},
        ]
        write_json(self.equity,{"stage":"V78.72","status":"PASS","equity_curve":curve})

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o76=self.r/"o76"
        a=build_reporting_foundation(self.cert,self.cfg,o76)
        o77=self.r/"o77"
        b=run_performance_report_builder(
            o76/"reporting_foundation_v78_76.json",
            self.metrics,self.equity,o77)
        o78=self.r/"o78"
        c=run_report_export_engine(
            o76/"reporting_foundation_v78_76.json",
            o77/"performance_report_builder_v78_77.json",o78)
        o79=self.r/"o79"
        d=run_reporting_safety_gate(
            o76/"reporting_foundation_v78_76.json",
            o77/"performance_report_builder_v78_77.json",
            o78/"report_export_engine_v78_78.json",o79)
        o80=self.r/"o80"
        e=issue_reporting_certificate(
            o76/"reporting_foundation_verification_v78_76.json",
            o77/"performance_report_builder_verification_v78_77.json",
            o78/"report_export_engine_verification_v78_78.json",
            o79/"reporting_safety_gate_verification_v78_79.json",
            o76/"reporting_foundation_v78_76.json",o80)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_report_hash_tamper_detected(self):
        payload=build_report_payload(load_json(self.metrics),load_json(self.equity),load_json(self.cfg)["reporting"])
        payload["summary"]["ending_equity"]=999
        self.assertIn("report_sha256",verify_report_payload(payload,["summary","trade_statistics","equity_curve","safety"]))

    def test_missing_section_detected(self):
        payload=build_report_payload(load_json(self.metrics),load_json(self.equity),load_json(self.cfg)["reporting"])
        del payload["summary"]
        errors=verify_report_payload(payload,["summary","trade_statistics","equity_curve","safety"])
        self.assertIn("missing_section:summary",errors)

    def test_markdown_contains_digest(self):
        payload=build_report_payload(load_json(self.metrics),load_json(self.equity),load_json(self.cfg)["reporting"])
        text=report_to_markdown(payload)
        self.assertIn(payload["report_sha256"],text)

    def test_csv_row_count(self):
        payload=build_report_payload(load_json(self.metrics),load_json(self.equity),load_json(self.cfg)["reporting"])
        rows=report_to_csv(payload).strip().splitlines()
        self.assertEqual(len(rows),3)

    def test_unsupported_export_blocked(self):
        cfg=load_json(self.cfg)
        cfg["reporting"]["export_formats"]=["pdf"]
        write_json(self.cfg,cfg)
        result=build_reporting_foundation(self.cert,self.cfg,self.r/"bad")
        self.assertEqual(result["status"],"FAIL")

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_DEPLOYMENT_PACKAGING_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.75","status":"FAIL"})
        self.assertEqual(
            build_reporting_foundation(self.cert,self.cfg,self.r/"badcert")["status"],
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
