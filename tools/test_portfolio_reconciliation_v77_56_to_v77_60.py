import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.portfolio_reconciliation_pipeline_v77_56_60 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.state=self.r/"state.json";write_json(self.state,{"stage":"V77.41","status":"PASS","portfolio_id":"P",
          "cash_balance":9000.0,"realized_pnl":0.0,"portfolio_state_sha256":"state",
          "positions":[{"symbol":"SPY","quantity":10,"average_cost":100.0,"market_price":100.0,"market_value":1000.0}]})
        self.fill=self.r/"fill.json";write_json(self.fill,{"stage":"V77.53","status":"PASS","fill_id":"F",
          "symbol":"SPY","side":"SELL","filled_quantity":3,"fill_price":110.0,"commission":0.0,"paper_fill_sha256":"fill"})
        self.cert=self.r/"cert.json";write_json(self.cert,{"certificate_id":"PAPER-EXECUTION-AUDIT-V77.55",
          "status":"PASS","certificate_sha256":"cert"})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o56=self.r/"o56";s56=reconcile_portfolio(self.state,self.fill,self.cert,o56);rec=o56/"portfolio_reconciliation_v77_56.json"
        o57=self.r/"o57";s57=build_cash_reconciliation_ledger(rec,o57);cash=o57/"cash_reconciliation_ledger_v77_57.json"
        o58=self.r/"o58";s58=build_position_reconciliation_ledger(self.state,rec,o58);pos=o58/"position_reconciliation_ledger_v77_58.json"
        o59=self.r/"o59";s59=run_reconciliation_safety_gate(rec,cash,pos,o59)
        o60=self.r/"o60";s60=issue_reconciliation_certificate(
          o56/"portfolio_reconciliation_verification_v77_56.json",
          o57/"cash_reconciliation_ledger_verification_v77_57.json",
          o58/"position_reconciliation_ledger_verification_v77_58.json",
          o59/"reconciliation_safety_gate_verification_v77_59.json",o60)
        return s56,s57,s58,s59,s60
    def test_full_chain(self):self.assertTrue(all(x.status=="PASS" for x in self.chain()))
    def test_sell_reconciliation_values(self):
        o=self.r/"o";reconcile_portfolio(self.state,self.fill,self.cert,o);d=load_json(o/"portfolio_reconciliation_v77_56.json")
        self.assertEqual(d["cash_after"],9330.0);self.assertEqual(d["position_quantity_after"],7);self.assertEqual(d["realized_pnl_after"],30.0)
    def test_buy_reconciliation_values(self):
        write_json(self.fill,{"stage":"V77.53","status":"PASS","fill_id":"F","symbol":"SPY","side":"BUY",
          "filled_quantity":2,"fill_price":120.0,"commission":0.0,"paper_fill_sha256":"fill"})
        o=self.r/"o";reconcile_portfolio(self.state,self.fill,self.cert,o);d=load_json(o/"portfolio_reconciliation_v77_56.json")
        self.assertEqual(d["cash_after"],8760.0);self.assertEqual(d["position_quantity_after"],12)
    def test_oversell_blocked(self):
        write_json(self.fill,{"stage":"V77.53","status":"PASS","fill_id":"F","symbol":"SPY","side":"SELL",
          "filled_quantity":99,"fill_price":110.0,"commission":0.0,"paper_fill_sha256":"fill"})
        with self.assertRaises(ReconciliationError):reconcile_portfolio(self.state,self.fill,self.cert,self.r/"o")
    def test_tampered_cash_blocked(self):
        o56=self.r/"o56";reconcile_portfolio(self.state,self.fill,self.cert,o56);rec=o56/"portfolio_reconciliation_v77_56.json"
        o57=self.r/"o57";build_cash_reconciliation_ledger(rec,o57);cash=o57/"cash_reconciliation_ledger_v77_57.json"
        d=load_json(cash);d["delta"]=1;d["cash_reconciliation_sha256"]=digest_json({k:v for k,v in d.items() if k!="cash_reconciliation_sha256"});write_json(cash,d)
        o58=self.r/"o58";build_position_reconciliation_ledger(self.state,rec,o58);pos=o58/"position_reconciliation_ledger_v77_58.json"
        self.assertEqual(run_reconciliation_safety_gate(rec,cash,pos,self.r/"o59").status,"FAIL")
    def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
