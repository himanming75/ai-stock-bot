import tempfile,unittest
from pathlib import Path
from strategy_runtime.strategy_runtime_pipeline_v78_36_40 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        write_json(self.cert,{
            "stage":"V78.35",
            "status":"PASS",
            "certification_scope":"OFFLINE_STRATEGY_RUNTIME_DEVELOPMENT_ONLY",
            "champion_candidate":{
                "candidate_id":"abc",
                "parameters":{"fast_window":3,"slow_window":5}
            }
        })
        write_json(self.cfg,{
            "strategy_runtime":{
                "strategy_id":"moving_average_cross_v78",
                "symbol":"AAPL",
                "minimum_history":5,
                "default_parameters":{"fast_window":3,"slow_window":5}
            }
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o36=self.r/"o36"
        a=build_strategy_runtime_foundation(self.cert,self.cfg,o36)
        o37=self.r/"o37"
        b=build_strategy_registry_context(o36/"strategy_runtime_foundation_v78_36.json",o37)
        o38=self.r/"o38"
        c=run_deterministic_signal_execution(o36/"strategy_runtime_foundation_v78_36.json",o38)
        o39=self.r/"o39"
        d=run_strategy_runtime_safety_gate(
            o36/"strategy_runtime_foundation_v78_36.json",
            o37/"strategy_registry_runtime_context_v78_37.json",
            o38/"deterministic_signal_execution_engine_v78_38.json",
            o39)
        o40=self.r/"o40"
        e=issue_strategy_runtime_certificate(
            o36/"strategy_runtime_foundation_verification_v78_36.json",
            o37/"strategy_registry_runtime_context_verification_v78_37.json",
            o38/"deterministic_signal_execution_engine_verification_v78_38.json",
            o39/"strategy_runtime_safety_gate_verification_v78_39.json",
            o36/"strategy_runtime_foundation_v78_36.json",
            o40)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_registry_duplicate_blocked(self):
        r=StrategyRegistry()
        s=MovingAverageCrossStrategy()
        r.register(s)
        with self.assertRaises(ValueError):
            r.register(s)

    def test_protocol_compliance(self):
        self.assertIsInstance(MovingAverageCrossStrategy(),StrategyRuntime)

    def test_invalid_windows_blocked(self):
        s=MovingAverageCrossStrategy()
        ctx=RuntimeContext("moving_average_cross_v78","c","AAPL",5,3,5)
        bars=[RuntimeBar("AAPL",f"2026-01-01T00:0{i}:00+00:00",100,1) for i in range(5)]
        with self.assertRaises(ValueError):
            s.evaluate(ctx,bars)

    def test_order_permission_blocked(self):
        s=MovingAverageCrossStrategy()
        ctx=RuntimeContext("moving_average_cross_v78","c","AAPL",3,5,5,True,False)
        bars=[RuntimeBar("AAPL",f"2026-01-01T00:0{i}:00+00:00",100,1) for i in range(5)]
        with self.assertRaises(ValueError):
            s.evaluate(ctx,bars)

    def test_timestamp_reorder_blocked(self):
        s=MovingAverageCrossStrategy()
        ctx=RuntimeContext("moving_average_cross_v78","c","AAPL",3,5,5)
        bars=[
            RuntimeBar("AAPL","2026-01-01T00:01:00+00:00",100,1),
            RuntimeBar("AAPL","2026-01-01T00:00:00+00:00",100,1),
        ]
        with self.assertRaises(ValueError):
            s.evaluate(ctx,bars)

    def test_signal_actions(self):
        signals=self.chain()[2]["signals"]
        self.assertTrue({"BUY","SELL","HOLD"}.issubset({x["action"] for x in signals}))

    def test_deterministic_signal(self):
        execution=self.chain()[2]
        self.assertTrue(execution["checks"]["deterministic_repeat"])

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_SIGNAL_RISK_BRIDGE_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.35","status":"FAIL"})
        result=build_strategy_runtime_foundation(self.cert,self.cfg,self.r/"bad")
        self.assertEqual(result["status"],"FAIL")

    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"])
            self.assertFalse(x["broker_connected"])

    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))

if __name__=="__main__":
    unittest.main()
