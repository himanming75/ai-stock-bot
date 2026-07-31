import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.risk_management_pipeline_v77_36_40 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";write_json(self.cert,{"certificate_id":"STRATEGY-INPUT-AUDIT-V77.35","status":"PASS","certificate_sha256":"abc"})
        features={"symbol":"SPY","close":500.0,"atr_14":1.5,"feature_sha256":"feat"}
        self.strategy=self.r/"strategy.json";write_json(self.strategy,{"stage":"V77.31","status":"PASS","feature_set":features})
        self.gate=self.r/"gate.json";write_json(self.gate,{"stage":"V77.34","status":"PASS","approved_signal":"BUY","signal_safety_gate_sha256":"gate"})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o36=self.r/"o36";s36=calculate_position_risk(self.cert,self.strategy,self.gate,o36);risk=o36/"position_risk_calculator_v77_36.json"
        o37=self.r/"o37";s37=apply_exposure_limits(risk,o37);ex=o37/"exposure_limit_engine_v77_37.json"
        o38=self.r/"o38";s38=build_exit_policy(risk,ex,o38);pol=o38/"stop_loss_take_profit_policy_v77_38.json"
        o39=self.r/"o39";s39=run_risk_decision_safety_gate(risk,ex,pol,o39)
        o40=self.r/"o40";s40=issue_risk_management_certificate(
          o36/"position_risk_calculator_verification_v77_36.json",o37/"exposure_limit_engine_verification_v77_37.json",
          o38/"stop_loss_take_profit_policy_verification_v77_38.json",o39/"risk_decision_safety_gate_verification_v77_39.json",o40)
        return s36,s37,s38,s39,s40
    def test_full_chain(self):self.assertTrue(all(x.status=="PASS" for x in self.chain()))
    def test_invalid_certificate(self):
        write_json(self.cert,{"certificate_id":"BAD","status":"PASS"})
        with self.assertRaises(RiskManagementError):calculate_position_risk(self.cert,self.strategy,self.gate,self.r/"x")
    def test_exposure_clips_position(self):
        o=self.r/"o";calculate_position_risk(self.cert,self.strategy,self.gate,o,account_equity=100000,risk_per_trade_pct=.05)
        r=o/"position_risk_calculator_v77_36.json";x=self.r/"x";apply_exposure_limits(r,x,max_symbol_exposure_pct=.01)
        d=load_json(x/"exposure_limit_engine_v77_37.json");self.assertLessEqual(d["approved_notional"],1000.01)
    def test_tamper_blocked(self):
        o36=self.r/"o36";calculate_position_risk(self.cert,self.strategy,self.gate,o36);risk=o36/"position_risk_calculator_v77_36.json"
        o37=self.r/"o37";apply_exposure_limits(risk,o37);ex=o37/"exposure_limit_engine_v77_37.json"
        d=load_json(ex);d["approved_quantity"]=-1;write_json(ex,d)
        o38=self.r/"o38";build_exit_policy(risk,ex,o38)
        self.assertEqual(run_risk_decision_safety_gate(risk,ex,o38/"stop_loss_take_profit_policy_v77_38.json",self.r/"o39").status,"FAIL")
    def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
