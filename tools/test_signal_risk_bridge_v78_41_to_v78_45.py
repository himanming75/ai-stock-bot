import tempfile,unittest
from pathlib import Path
from signal_risk_bridge.signal_risk_bridge_pipeline_v78_41_45 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        self.signals=self.r/"signals.json"

        write_json(self.cert,{
            "stage":"V78.40",
            "status":"PASS",
            "certification_scope":"OFFLINE_SIGNAL_RISK_BRIDGE_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"}
        })
        write_json(self.cfg,{
            "signal_risk_bridge":{
                "confidence_map":{"BUY":0.75,"SELL":0.75,"HOLD":0.0},
                "max_requested_notional":1000.0,
                "reference_price":100.0,
                "current_cash":100000.0,
                "current_position_quantity":10,
                "risk_limits":{
                    "max_position_notional":1000.0,
                    "min_order_notional":50.0,
                    "max_cash_utilization":0.1
                }
            }
        })
        write_json(self.signals,{
            "stage":"V78.38",
            "status":"PASS",
            "signals":[
                {"signal_id":"s1","strategy_id":"x","candidate_id":"abc","symbol":"AAPL",
                 "timestamp":"2026-01-01T00:00:00+00:00","action":"BUY"},
                {"signal_id":"s2","strategy_id":"x","candidate_id":"abc","symbol":"AAPL",
                 "timestamp":"2026-01-01T00:01:00+00:00","action":"SELL"},
                {"signal_id":"s3","strategy_id":"x","candidate_id":"abc","symbol":"AAPL",
                 "timestamp":"2026-01-01T00:02:00+00:00","action":"HOLD"}
            ]
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o41=self.r/"o41"
        a=build_signal_risk_bridge_foundation(self.cert,self.cfg,o41)
        o42=self.r/"o42"
        b=run_signal_normalization_risk_request(
            o41/"signal_risk_bridge_foundation_v78_41.json",
            self.signals,
            o42)
        o43=self.r/"o43"
        c=run_risk_decision_integration(
            o41/"signal_risk_bridge_foundation_v78_41.json",
            o42/"signal_normalization_risk_request_v78_42.json",
            o43)
        o44=self.r/"o44"
        d=run_signal_risk_safety_gate(
            o41/"signal_risk_bridge_foundation_v78_41.json",
            o42/"signal_normalization_risk_request_v78_42.json",
            o43/"risk_decision_integration_v78_43.json",
            o44)
        o45=self.r/"o45"
        e=issue_signal_risk_bridge_certificate(
            o41/"signal_risk_bridge_foundation_verification_v78_41.json",
            o42/"signal_normalization_risk_request_verification_v78_42.json",
            o43/"risk_decision_integration_verification_v78_43.json",
            o44/"signal_risk_safety_gate_verification_v78_44.json",
            o41/"signal_risk_bridge_foundation_v78_41.json",
            o45)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_hold_creates_no_request(self):
        s=normalize_signal({
            "signal_id":"x","strategy_id":"s","candidate_id":"c","symbol":"AAPL",
            "timestamp":"t","action":"HOLD"
        },{"HOLD":0.0})
        self.assertIsNone(build_risk_request(s,100,1000,10,500))

    def test_buy_request_capped_by_cash(self):
        s=normalize_signal({
            "signal_id":"x","strategy_id":"s","candidate_id":"c","symbol":"AAPL",
            "timestamp":"t","action":"BUY"
        },{"BUY":1.0})
        r=build_risk_request(s,100,300,0,1000)
        self.assertEqual(r.requested_notional,300)

    def test_sell_request_capped_by_position(self):
        s=normalize_signal({
            "signal_id":"x","strategy_id":"s","candidate_id":"c","symbol":"AAPL",
            "timestamp":"t","action":"SELL"
        },{"SELL":1.0})
        r=build_risk_request(s,100,1000,2,1000)
        self.assertEqual(r.requested_notional,200)

    def test_risk_buy_approval(self):
        s=normalize_signal({
            "signal_id":"x","strategy_id":"s","candidate_id":"c","symbol":"AAPL",
            "timestamp":"t","action":"BUY"
        },{"BUY":1.0})
        r=build_risk_request(s,100,1000,0,500)
        d=evaluate_risk_request(r,500,50,0.5)
        self.assertEqual(d.decision,"APPROVE")
        self.assertEqual(d.approved_quantity,5)

    def test_below_minimum_rejected(self):
        s=normalize_signal({
            "signal_id":"x","strategy_id":"s","candidate_id":"c","symbol":"AAPL",
            "timestamp":"t","action":"BUY"
        },{"BUY":1.0})
        r=build_risk_request(s,100,20,0,20)
        d=evaluate_risk_request(r,500,50,0.5)
        self.assertEqual(d.decision,"REJECT")

    def test_invalid_action_blocked(self):
        with self.assertRaises(ValueError):
            normalize_signal({
                "signal_id":"x","strategy_id":"s","candidate_id":"c","symbol":"AAPL",
                "timestamp":"t","action":"WAIT"
            },{})

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_PORTFOLIO_RUNTIME_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.40","status":"FAIL"})
        self.assertEqual(
            build_signal_risk_bridge_foundation(self.cert,self.cfg,self.r/"bad")["status"],
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
