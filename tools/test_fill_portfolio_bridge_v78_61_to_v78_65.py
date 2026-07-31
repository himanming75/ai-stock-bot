import tempfile,unittest
from pathlib import Path
from fill_portfolio_bridge.fill_portfolio_bridge_pipeline_v78_61_65 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        self.fills=self.r/"fills.json"

        write_json(self.cert,{
            "stage":"V78.60","status":"PASS",
            "certification_scope":"OFFLINE_FILL_PORTFOLIO_BRIDGE_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"}
        })
        write_json(self.cfg,{
            "fill_portfolio_bridge":{
                "starting_cash":100000.0,
                "mark_prices":{"AAPL":100.0},
                "allow_real_broker_events":False
            }
        })
        write_json(self.fills,{
            "stage":"V78.58","status":"PASS",
            "paper_fills":[
                {"fill_id":"f1","broker_order_id":"b1","order_intent_id":"i1","symbol":"AAPL",
                 "side":"buy","fill_quantity":4,"fill_price":100.05,"gross_notional":400.2,
                 "commission":0.25,"slippage_cost":0.2,"remaining_quantity":6,
                 "fill_status":"PARTIALLY_FILLED","fill_sha256":"x"},
                {"fill_id":"f2","broker_order_id":"b1","order_intent_id":"i1","symbol":"AAPL",
                 "side":"buy","fill_quantity":4,"fill_price":100.05,"gross_notional":400.2,
                 "commission":0.25,"slippage_cost":0.2,"remaining_quantity":2,
                 "fill_status":"PARTIALLY_FILLED","fill_sha256":"y"},
                {"fill_id":"f3","broker_order_id":"b1","order_intent_id":"i1","symbol":"AAPL",
                 "side":"buy","fill_quantity":2,"fill_price":100.05,"gross_notional":200.1,
                 "commission":0.25,"slippage_cost":0.1,"remaining_quantity":0,
                 "fill_status":"FILLED","fill_sha256":"z"},
                {"fill_id":"f4","broker_order_id":"b2","order_intent_id":"i2","symbol":"AAPL",
                 "side":"sell","fill_quantity":4,"fill_price":99.95,"gross_notional":399.8,
                 "commission":0.25,"slippage_cost":0.2,"remaining_quantity":6,
                 "fill_status":"PARTIALLY_FILLED","fill_sha256":"a"},
                {"fill_id":"f5","broker_order_id":"b2","order_intent_id":"i2","symbol":"AAPL",
                 "side":"sell","fill_quantity":4,"fill_price":99.95,"gross_notional":399.8,
                 "commission":0.25,"slippage_cost":0.2,"remaining_quantity":2,
                 "fill_status":"PARTIALLY_FILLED","fill_sha256":"b"},
                {"fill_id":"f6","broker_order_id":"b2","order_intent_id":"i2","symbol":"AAPL",
                 "side":"sell","fill_quantity":2,"fill_price":99.95,"gross_notional":199.9,
                 "commission":0.25,"slippage_cost":0.1,"remaining_quantity":0,
                 "fill_status":"FILLED","fill_sha256":"c"}
            ]
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o61=self.r/"o61"
        a=build_fill_portfolio_bridge_foundation(self.cert,self.cfg,o61)
        o62=self.r/"o62"
        b=run_fill_normalization_portfolio_event(
            o61/"fill_portfolio_bridge_foundation_v78_61.json",
            self.fills,o62)
        o63=self.r/"o63"
        c=run_fill_application_reconciliation(
            o61/"fill_portfolio_bridge_foundation_v78_61.json",
            o62/"fill_normalization_portfolio_event_v78_62.json",o63)
        o64=self.r/"o64"
        d=run_fill_portfolio_safety_gate(
            o61/"fill_portfolio_bridge_foundation_v78_61.json",
            o62/"fill_normalization_portfolio_event_v78_62.json",
            o63/"fill_application_reconciliation_v78_63.json",o64)
        o65=self.r/"o65"
        e=issue_fill_portfolio_bridge_certificate(
            o61/"fill_portfolio_bridge_foundation_verification_v78_61.json",
            o62/"fill_normalization_portfolio_event_verification_v78_62.json",
            o63/"fill_application_reconciliation_verification_v78_63.json",
            o64/"fill_portfolio_safety_gate_verification_v78_64.json",
            o61/"fill_portfolio_bridge_foundation_v78_61.json",o65)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_gross_mismatch_blocked(self):
        with self.assertRaises(ValueError):
            normalize_fill({
                "fill_id":"f","broker_order_id":"b","order_intent_id":"i","symbol":"AAPL",
                "side":"buy","fill_quantity":2,"fill_price":100,"gross_notional":199,
                "commission":0,"slippage_cost":0,"remaining_quantity":0,"fill_status":"FILLED"
            })

    def test_duplicate_fill_blocked(self):
        fill=normalize_fill({
            "fill_id":"f","broker_order_id":"b","order_intent_id":"i","symbol":"AAPL",
            "side":"buy","fill_quantity":1,"fill_price":100,"gross_notional":100,
            "commission":0,"slippage_cost":0,"remaining_quantity":0,"fill_status":"FILLED"
        })
        runtime=FillPortfolioRuntime(1000)
        runtime.apply(fill)
        with self.assertRaises(ValueError):
            runtime.apply(fill)

    def test_buy_commission_in_average_cost(self):
        fill=normalize_fill({
            "fill_id":"f","broker_order_id":"b","order_intent_id":"i","symbol":"AAPL",
            "side":"buy","fill_quantity":2,"fill_price":100,"gross_notional":200,
            "commission":2,"slippage_cost":0,"remaining_quantity":0,"fill_status":"FILLED"
        })
        runtime=FillPortfolioRuntime(1000)
        runtime.apply(fill)
        self.assertEqual(runtime.positions["AAPL"]["average_cost"],101.0)

    def test_sell_realized_pnl(self):
        buy=normalize_fill({
            "fill_id":"fb","broker_order_id":"b1","order_intent_id":"i1","symbol":"AAPL",
            "side":"buy","fill_quantity":2,"fill_price":100,"gross_notional":200,
            "commission":0,"slippage_cost":0,"remaining_quantity":0,"fill_status":"FILLED"
        })
        sell=normalize_fill({
            "fill_id":"fs","broker_order_id":"b2","order_intent_id":"i2","symbol":"AAPL",
            "side":"sell","fill_quantity":1,"fill_price":110,"gross_notional":110,
            "commission":1,"slippage_cost":0,"remaining_quantity":0,"fill_status":"FILLED"
        })
        runtime=FillPortfolioRuntime(1000)
        runtime.apply(buy);runtime.apply(sell)
        self.assertEqual(runtime.realized_pnl,9.0)

    def test_replay_hash_tamper_blocked(self):
        fill=normalize_fill({
            "fill_id":"f","broker_order_id":"b","order_intent_id":"i","symbol":"AAPL",
            "side":"buy","fill_quantity":1,"fill_price":100,"gross_notional":100,
            "commission":0,"slippage_cost":0,"remaining_quantity":0,"fill_status":"FILLED"
        })
        runtime=FillPortfolioRuntime(1000)
        event=runtime.apply(fill)
        bad=PortfolioFillEvent(**{**asdict(event),"cash_delta":-99})
        with self.assertRaises(ValueError):
            replay_fill_events(1000,[bad])

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_AUDIT_RECONCILIATION_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.60","status":"FAIL"})
        self.assertEqual(
            build_fill_portfolio_bridge_foundation(self.cert,self.cfg,self.r/"bad")["status"],
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
