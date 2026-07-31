import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.portfolio_management_pipeline_v77_41_45 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";write_json(self.cert,{"certificate_id":"RISK-MANAGEMENT-AUDIT-V77.40","status":"PASS","certificate_sha256":"abc"})
        self.gate=self.r/"gate.json";write_json(self.gate,{"stage":"V77.39","status":"PASS","approved_quantity":100,"risk_safety_gate_sha256":"gate"})
        self.strategy=self.r/"strategy.json";write_json(self.strategy,{"stage":"V77.31","status":"PASS","feature_set":{"symbol":"SPY","close":500.0}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o41=self.r/"o41";s41=build_paper_portfolio_state(self.cert,self.gate,self.strategy,o41);st=o41/"paper_portfolio_state_v77_41.json"
        o42=self.r/"o42";s42=build_position_ledger(st,o42);ld=o42/"portfolio_position_ledger_v77_42.json"
        o43=self.r/"o43";s43=value_portfolio(st,ld,o43);va=o43/"portfolio_valuation_v77_43.json"
        o44=self.r/"o44";s44=run_portfolio_safety_gate(st,ld,va,o44)
        o45=self.r/"o45";s45=issue_portfolio_certificate(
          o41/"paper_portfolio_state_verification_v77_41.json",o42/"portfolio_position_ledger_verification_v77_42.json",
          o43/"portfolio_valuation_verification_v77_43.json",o44/"portfolio_safety_gate_verification_v77_44.json",o45)
        return s41,s42,s43,s44,s45
    def test_full_chain(self):self.assertTrue(all(x.status=="PASS" for x in self.chain()))
    def test_invalid_certificate(self):
        write_json(self.cert,{"certificate_id":"BAD","status":"PASS"})
        with self.assertRaises(PortfolioManagementError):build_paper_portfolio_state(self.cert,self.gate,self.strategy,self.r/"x")
    def test_negative_cash_blocked(self):
        o41=self.r/"o41";build_paper_portfolio_state(self.cert,self.gate,self.strategy,o41);st=o41/"paper_portfolio_state_v77_41.json"
        d=load_json(st);d["cash_balance"]=-1;d["portfolio_state_sha256"]=digest_json({k:v for k,v in d.items() if k!="portfolio_state_sha256"});write_json(st,d)
        o42=self.r/"o42";build_position_ledger(st,o42);ld=o42/"portfolio_position_ledger_v77_42.json"
        o43=self.r/"o43";value_portfolio(st,ld,o43)
        self.assertEqual(run_portfolio_safety_gate(st,ld,o43/"portfolio_valuation_v77_43.json",self.r/"o44").status,"FAIL")
    def test_duplicate_position_detected(self):
        o41=self.r/"o41";build_paper_portfolio_state(self.cert,self.gate,self.strategy,o41);st=o41/"paper_portfolio_state_v77_41.json"
        d=load_json(st);d["positions"].append(dict(d["positions"][0]));d["portfolio_state_sha256"]=digest_json({k:v for k,v in d.items() if k!="portfolio_state_sha256"});write_json(st,d)
        self.assertEqual(build_position_ledger(st,self.r/"o42").status,"FAIL")
    def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
