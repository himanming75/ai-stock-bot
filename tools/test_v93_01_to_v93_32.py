import tempfile, unittest
from pathlib import Path
from market_regime_engine.indicators import (
    sma, annualized_volatility, momentum,
    average_true_range_pct, trend_slope_pct,
)
from market_regime_engine.classifier import classify_regime
from market_regime_engine.strategy_mapping import (
    recommend_strategies, position_multiplier,
)
from market_regime_engine.engine import evaluate

def bars(n=120):
    out=[];c=100.0
    for i in range(n):
        c += .5
        out.append({"timestamp":str(i),"open":c-.2,"high":c+.5,"low":c-.5,"close":c,"volume":1000})
    return out

class Tests(unittest.TestCase):
    def test_sma(self): self.assertEqual(sma([1,2,3],2),2.5)
    def test_volatility(self): self.assertGreaterEqual(annualized_volatility([1,2,3]),0)
    def test_momentum(self): self.assertGreater(momentum([1,2,3,4],2),0)
    def test_atr(self): self.assertGreater(average_true_range_pct(bars(),14),0)
    def test_slope(self): self.assertGreater(trend_slope_pct([1,2,3,4],3),0)
    def test_bull(self):
        r=classify_regime({"trend_slope_pct":5,"momentum_pct":4,"annualized_volatility_pct":20,"atr_pct":1,"price_above_long_sma":True},{})
        self.assertEqual(r["primary_regime"],"BULL")
    def test_bear(self):
        r=classify_regime({"trend_slope_pct":-5,"momentum_pct":-4,"annualized_volatility_pct":20,"atr_pct":1,"price_above_long_sma":False},{})
        self.assertEqual(r["primary_regime"],"BEAR")
    def test_mapping(self):
        self.assertIn("MOMENTUM",recommend_strategies({"primary_regime":"BULL"},["MOMENTUM"]))
    def test_multiplier(self):
        self.assertLessEqual(position_multiplier({"primary_regime":"BEAR","volatility_regime":"HIGH_VOLATILITY","risk_mode":"RISK_OFF"}),1)
    def test_missing_data(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],"MARKET_REGIME_HISTORICAL_DATA_REQUIRED")
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__": unittest.main()
