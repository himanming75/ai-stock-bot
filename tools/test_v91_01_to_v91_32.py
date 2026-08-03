import json, tempfile, unittest
from pathlib import Path
from strategy_lab.registry import StrategyRegistry, StrategyDefinition
from strategy_lab.adapter import base_strategy_name
from strategy_lab.scoring import champion_score
from strategy_lab.engine import run_lab

class Tests(unittest.TestCase):
    def test_registry_defaults(self):
        r=StrategyRegistry();r.register_defaults()
        self.assertGreaterEqual(len(r.all()),10)
    def test_duplicate_rejected(self):
        r=StrategyRegistry()
        d=StrategyDefinition("X","X","test","x",{})
        r.register(d)
        with self.assertRaises(ValueError): r.register(d)
    def test_adapter_ema(self): self.assertEqual(base_strategy_name("EMA_FAST_5_20"),"EMA_CROSS")
    def test_adapter_rsi(self): self.assertEqual(base_strategy_name("RSI_30_70"),"RSI")
    def test_score_prefers_approved(self):
        a={"total_return_pct":10,"sharpe_ratio":1,"maximum_drawdown_pct":5,"profit_factor":2,"win_rate_pct":60,"gate":{"approved":True,"excess_return_pct":1}}
        b={**a,"gate":{"approved":False,"excess_return_pct":1}}
        self.assertGreater(champion_score(a),champion_score(b))
    def test_missing_data_state(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run_lab(Path(t))["state"],"STRATEGY_LAB_HISTORICAL_DATA_REQUIRED")
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            result=run_lab(Path(t))
            self.assertFalse(result["order_submission_enabled"])
    def test_registry_serializable(self):
        r=StrategyRegistry();r.register_defaults()
        json.dumps([x.to_dict() for x in r.all()])
    def test_enabled(self):
        r=StrategyRegistry();r.register_defaults()
        self.assertEqual(len(r.enabled()),len(r.all()))
    def test_unknown_adapter(self):
        with self.assertRaises(ValueError): base_strategy_name("UNKNOWN")

if __name__=="__main__":unittest.main()
