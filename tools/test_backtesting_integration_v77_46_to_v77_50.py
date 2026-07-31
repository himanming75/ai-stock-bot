import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.backtesting_integration_pipeline_v77_46_50 import *
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
  self.cert=self.r/"cert.json";write_json(self.cert,{"certificate_id":"PORTFOLIO-AUDIT-V77.45","status":"PASS","certificate_sha256":"abc"})
  self.strategy=self.r/"strategy.json";write_json(self.strategy,{"stage":"V77.31","status":"PASS","feature_set":{"symbol":"SPY","close":500.0,"feature_sha256":"f"}})
  self.state=self.r/"state.json";write_json(self.state,{"stage":"V77.41","status":"PASS","starting_cash":100000.0})
 def tearDown(self):self.t.cleanup()
 def chain(self):
  o46=self.r/"o46";s46=adapt_backtest_input(self.cert,self.strategy,self.state,o46);inp=o46/"backtest_input_adapter_v77_46.json"
  o47=self.r/"o47";s47=replay_historical_data(inp,o47);rep=o47/"historical_data_replay_v77_47.json"
  o48=self.r/"o48";s48=simulate_strategy_execution(rep,o48);sim=o48/"strategy_execution_simulation_v77_48.json"
  o49=self.r/"o49";s49=run_backtest_safety_gate(inp,rep,sim,o49)
  o50=self.r/"o50";s50=issue_backtest_certificate(o46/"backtest_input_adapter_verification_v77_46.json",
    o47/"historical_data_replay_verification_v77_47.json",o48/"strategy_execution_simulation_verification_v77_48.json",
    o49/"backtest_safety_gate_verification_v77_49.json",o50)
  return s46,s47,s48,s49,s50
 def test_full_chain(self):self.assertTrue(all(x.status=="PASS" for x in self.chain()))
 def test_invalid_certificate(self):
  write_json(self.cert,{"certificate_id":"BAD","status":"PASS"})
  with self.assertRaises(BacktestingIntegrationError):adapt_backtest_input(self.cert,self.strategy,self.state,self.r/"x")
 def test_insufficient_bars(self):
  p=self.r/"x.json";write_json(p,{"stage":"V77.46","bar_count":1,"bars":[]})
  with self.assertRaises(BacktestingIntegrationError):replay_historical_data(p,self.r/"o")
 def test_tamper_blocked(self):
  o46=self.r/"o46";adapt_backtest_input(self.cert,self.strategy,self.state,o46);inp=o46/"backtest_input_adapter_v77_46.json"
  o47=self.r/"o47";replay_historical_data(inp,o47);rep=o47/"historical_data_replay_v77_47.json"
  o48=self.r/"o48";simulate_strategy_execution(rep,o48);sim=o48/"strategy_execution_simulation_v77_48.json"
  d=load_json(sim);d["actual_orders_submitted"]=1;d["execution_simulation_sha256"]=digest_json({k:v for k,v in d.items() if k!="execution_simulation_sha256"});write_json(sim,d)
  self.assertEqual(run_backtest_safety_gate(inp,rep,sim,self.r/"o49").status,"FAIL")
 def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
