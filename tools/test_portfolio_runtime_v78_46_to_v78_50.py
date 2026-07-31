import tempfile,unittest
from pathlib import Path
from portfolio_runtime.portfolio_runtime_pipeline_v78_46_50 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        self.decisions=self.r/"decisions.json"
        self.normalization=self.r/"normalization.json"

        write_json(self.cert,{
            "stage":"V78.45","status":"PASS",
            "certification_scope":"OFFLINE_PORTFOLIO_RUNTIME_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"}
        })
        write_json(self.cfg,{
            "portfolio_runtime":{
                "starting_cash":100000.0,
                "mark_prices":{"AAPL":100.0},
                "allow_order_creation":False,
                "allow_order_submission":False
            }
        })
        write_json(self.normalization,{
            "stage":"V78.42","status":"PASS",
            "risk_requests":[
                {"risk_request_id":"r1","normalized_signal_id":"n1","candidate_id":"abc",
                 "symbol":"AAPL","timestamp":"t1","side":"buy","requested_notional":1000.0,
                 "reference_price":100.0,"current_cash":100000.0,"current_position_quantity":10,
                 "risk_request_sha256":"x"},
                {"risk_request_id":"r2","normalized_signal_id":"n2","candidate_id":"abc",
                 "symbol":"AAPL","timestamp":"t2","side":"sell","requested_notional":1000.0,
                 "reference_price":100.0,"current_cash":100000.0,"current_position_quantity":10,
                 "risk_request_sha256":"y"}
            ]
        })
        write_json(self.decisions,{
            "stage":"V78.43","status":"PASS",
            "risk_decisions":[
                {"risk_decision_id":"d1","risk_request_id":"r1","decision":"APPROVE",
                 "approved_notional":1000.0,"approved_quantity":10,"reason":"ok","risk_decision_sha256":"a"},
                {"risk_decision_id":"d2","risk_request_id":"r2","decision":"APPROVE",
                 "approved_notional":1000.0,"approved_quantity":10,"reason":"ok","risk_decision_sha256":"b"}
            ]
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o46=self.r/"o46"
        a=build_portfolio_runtime_foundation(self.cert,self.cfg,o46)
        o47=self.r/"o47"
        b=build_portfolio_state_position_ledger(
            o46/"portfolio_runtime_foundation_v78_46.json",
            self.decisions,self.normalization,o47)
        o48=self.r/"o48"
        c=run_approved_decision_application_engine(
            o46/"portfolio_runtime_foundation_v78_46.json",o48)
        o49=self.r/"o49"
        d=run_portfolio_runtime_safety_gate(
            o46/"portfolio_runtime_foundation_v78_46.json",
            o47/"portfolio_state_position_ledger_v78_47.json",
            o48/"approved_decision_application_engine_v78_48.json",o49)
        o50=self.r/"o50"
        e=issue_portfolio_runtime_certificate(
            o46/"portfolio_runtime_foundation_verification_v78_46.json",
            o47/"portfolio_state_position_ledger_verification_v78_47.json",
            o48/"approved_decision_application_engine_verification_v78_48.json",
            o49/"portfolio_runtime_safety_gate_verification_v78_49.json",
            o46/"portfolio_runtime_foundation_v78_46.json",o50)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_buy_updates_cash_and_position(self):
        p=PortfolioRuntime(1000)
        req={"risk_request_id":"r","symbol":"AAPL","side":"buy","reference_price":100}
        dec={"risk_decision_id":"d","risk_request_id":"r","decision":"APPROVE","approved_quantity":5}
        p.apply_approved_decision(dec,req)
        s=p.snapshot()
        self.assertEqual(s["cash"],500)
        self.assertEqual(s["positions"][0]["quantity"],5)

    def test_sell_realized_pnl(self):
        p=PortfolioRuntime(1000)
        p.apply_approved_decision(
            {"risk_decision_id":"d1","risk_request_id":"r1","decision":"APPROVE","approved_quantity":5},
            {"risk_request_id":"r1","symbol":"AAPL","side":"buy","reference_price":100})
        p.apply_approved_decision(
            {"risk_decision_id":"d2","risk_request_id":"r2","decision":"APPROVE","approved_quantity":2},
            {"risk_request_id":"r2","symbol":"AAPL","side":"sell","reference_price":110})
        self.assertEqual(p.snapshot()["realized_pnl"],20)

    def test_oversell_blocked(self):
        p=PortfolioRuntime(1000)
        with self.assertRaises(ValueError):
            p.apply_approved_decision(
                {"risk_decision_id":"d","risk_request_id":"r","decision":"APPROVE","approved_quantity":1},
                {"risk_request_id":"r","symbol":"AAPL","side":"sell","reference_price":100})

    def test_duplicate_reference_blocked(self):
        p=PortfolioRuntime(1000)
        req={"risk_request_id":"r","symbol":"AAPL","side":"buy","reference_price":100}
        dec={"risk_decision_id":"d","risk_request_id":"r","decision":"APPROVE","approved_quantity":1}
        p.apply_approved_decision(dec,req)
        with self.assertRaises(ValueError):
            p.apply_approved_decision(dec,req)

    def test_rejected_decision_ignored(self):
        p=PortfolioRuntime(1000)
        result=p.apply_approved_decision(
            {"risk_decision_id":"d","risk_request_id":"r","decision":"REJECT","approved_quantity":0},
            {"risk_request_id":"r","symbol":"AAPL","side":"buy","reference_price":100})
        self.assertIsNone(result)
        self.assertEqual(p.snapshot()["ledger_count"],0)

    def test_replay(self):
        p=PortfolioRuntime(1000)
        p.apply_approved_decision(
            {"risk_decision_id":"d1","risk_request_id":"r1","decision":"APPROVE","approved_quantity":2},
            {"risk_request_id":"r1","symbol":"AAPL","side":"buy","reference_price":100})
        state=replay_portfolio(1000,p.ledger)
        self.assertEqual(state["cash"],800)
        self.assertEqual(state["positions"][0]["quantity"],2)

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_EXECUTION_COORDINATOR_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.45","status":"FAIL"})
        self.assertEqual(
            build_portfolio_runtime_foundation(self.cert,self.cfg,self.r/"bad")["status"],
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
