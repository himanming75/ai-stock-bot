import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.strategy_input_pipeline_v77_31_35 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";write_json(self.cert,{"certificate_id":"MARKET-DATA-AUDIT-V77.30","status":"PASS","certificate_sha256":"abc"})
        bars=[]
        for i in range(30):
            o=500+i*.1;c=o+(((i%7)-3)*.05)
            bars.append({"sequence":i+1,"symbol":"SPY","timestamp_utc":f"2026-01-02T14:{30+i:02d}:00+00:00",
              "open":o,"high":max(o,c)+.2,"low":min(o,c)-.2,"close":c,"volume":1000+i})
        self.feed=self.r/"feed.json";write_json(self.feed,{"stage":"V77.26","status":"PASS","symbol":"SPY","bars":bars,"feed_sha256":"feed"})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o31=self.r/"o31";s31=build_strategy_input(self.cert,self.feed,o31);si=o31/"ai_strategy_input_v77_31.json"
        o32=self.r/"o32";s32=build_feature_validation_ledger(si,o32);ld=o32/"strategy_feature_validation_ledger_v77_32.json"
        o33=self.r/"o33";s33=generate_strategy_signal(si,ld,o33);sg=o33/"strategy_signal_v77_33.json"
        o34=self.r/"o34";s34=run_signal_safety_gate(sg,si,o34)
        o35=self.r/"o35";s35=issue_strategy_input_certificate(
          o31/"ai_strategy_input_verification_v77_31.json",o32/"strategy_feature_validation_ledger_verification_v77_32.json",
          o33/"strategy_signal_verification_v77_33.json",o34/"signal_safety_gate_verification_v77_34.json",o35)
        return s31,s32,s33,s34,s35
    def test_full_chain(self):self.assertTrue(all(x.status=="PASS" for x in self.chain()))
    def test_invalid_certificate(self):
        write_json(self.cert,{"certificate_id":"BAD","status":"PASS"})
        with self.assertRaises(StrategyInputError):build_strategy_input(self.cert,self.feed,self.r/"x")
    def test_insufficient_bars(self):
        d=load_json(self.feed);d["bars"]=d["bars"][:10];write_json(self.feed,d)
        with self.assertRaises(StrategyInputError):build_strategy_input(self.cert,self.feed,self.r/"x")
    def test_signal_tamper_blocked(self):
        o31=self.r/"o31";build_strategy_input(self.cert,self.feed,o31);si=o31/"ai_strategy_input_v77_31.json"
        o32=self.r/"o32";build_feature_validation_ledger(si,o32)
        o33=self.r/"o33";generate_strategy_signal(si,o32/"strategy_feature_validation_ledger_v77_32.json",o33)
        sg=o33/"strategy_signal_v77_33.json";d=load_json(sg);d["signal"]="BAD";write_json(sg,d)
        self.assertEqual(run_signal_safety_gate(sg,si,self.r/"o34").status,"FAIL")
    def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
