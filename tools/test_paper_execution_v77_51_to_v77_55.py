import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.paper_execution_pipeline_v77_51_55 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";write_json(self.cert,{"certificate_id":"BACKTEST-AUDIT-V77.50","status":"PASS","certificate_sha256":"abc"})
        self.sim=self.r/"sim.json";write_json(self.sim,{"stage":"V77.48","status":"PASS","execution_simulation_sha256":"sim",
          "trades":[{"side":"BUY","quantity":10,"price":100.0}]})
        self.state=self.r/"state.json";write_json(self.state,{"stage":"V77.41","status":"PASS","buying_power":10000.0,"cash_balance":10000.0,
          "positions":[{"symbol":"SPY","quantity":10,"market_price":100.0}]})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o51=self.r/"o51";s51=build_paper_order_intent(self.cert,self.sim,self.state,o51);intent=o51/"paper_order_intent_v77_51.json"
        o52=self.r/"o52";s52=validate_paper_order(intent,self.state,o52);val=o52/"paper_order_validation_v77_52.json"
        o53=self.r/"o53";s53=simulate_paper_fill(intent,val,o53);fill=o53/"paper_fill_simulation_v77_53.json"
        o54=self.r/"o54";s54=run_paper_execution_safety_gate(intent,val,fill,o54)
        o55=self.r/"o55";s55=issue_paper_execution_certificate(
          o51/"paper_order_intent_verification_v77_51.json",o52/"paper_order_validation_verification_v77_52.json",
          o53/"paper_fill_simulation_verification_v77_53.json",o54/"paper_execution_safety_gate_verification_v77_54.json",o55)
        return s51,s52,s53,s54,s55
    def test_full_chain(self):self.assertTrue(all(x.status=="PASS" for x in self.chain()))
    def test_real_portfolio_capacity_adjustment(self):
        write_json(self.state,{"stage":"V77.41","status":"PASS","buying_power":0.0,"cash_balance":0.0,
          "positions":[{"symbol":"SPY","quantity":3,"market_price":100.0}]})
        write_json(self.sim,{"stage":"V77.48","status":"PASS","execution_simulation_sha256":"sim",
          "trades":[{"side":"BUY","quantity":999,"price":100.0}]})
        o=self.r/"adjusted";build_paper_order_intent(self.cert,self.sim,self.state,o)
        intent=load_json(o/"paper_order_intent_v77_51.json")
        self.assertEqual(intent["side"],"SELL")
        self.assertEqual(intent["quantity"],3)
        self.assertEqual(validate_paper_order(o/"paper_order_intent_v77_51.json",self.state,self.r/"validated").status,"PASS")
    def test_invalid_certificate(self):
        write_json(self.cert,{"certificate_id":"BAD","status":"PASS"})
        with self.assertRaises(PaperExecutionError):build_paper_order_intent(self.cert,self.sim,self.state,self.r/"x")
    def test_insufficient_buying_power(self):
        write_json(self.state,{"stage":"V77.41","buying_power":1.0,"cash_balance":1.0,"positions":[]})
        intent=self.r/"manual_intent.json"
        doc={"stage":"V77.51","status":"PASS","intent_id":"TEST","symbol":"SPY","side":"BUY",
             "quantity":10,"reference_price":100.0,"paper_only":True}
        doc["paper_order_intent_sha256"]=digest_json({k:v for k,v in doc.items() if k!="paper_order_intent_sha256"})
        write_json(intent,doc)
        self.assertEqual(validate_paper_order(intent,self.state,self.r/"v").status,"FAIL")
    def test_tampered_fill_blocked(self):
        o51=self.r/"o51";build_paper_order_intent(self.cert,self.sim,self.state,o51);intent=o51/"paper_order_intent_v77_51.json"
        o52=self.r/"o52";validate_paper_order(intent,self.state,o52);val=o52/"paper_order_validation_v77_52.json"
        o53=self.r/"o53";simulate_paper_fill(intent,val,o53);fill=o53/"paper_fill_simulation_v77_53.json"
        d=load_json(fill);d["actual_orders_submitted"]=1;d["paper_fill_sha256"]=digest_json({k:v for k,v in d.items() if k!="paper_fill_sha256"});write_json(fill,d)
        self.assertEqual(run_paper_execution_safety_gate(intent,val,fill,self.r/"o54").status,"FAIL")
    def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
