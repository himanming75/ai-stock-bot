import tempfile, unittest
from pathlib import Path
from multi_timeframe_regime.resample import resample_bars
from multi_timeframe_regime.consensus import build_consensus
from multi_timeframe_regime.decision import position_multiplier, recommend_strategies
from multi_timeframe_regime.engine import evaluate

def bars(n=90):
    out=[];c=100.0
    for i in range(n):
        c += .4
        out.append({"timestamp":str(i),"open":c-.1,"high":c+.5,"low":c-.5,"close":c,"volume":1000})
    return out

class Tests(unittest.TestCase):
    def test_resample(self):
        self.assertEqual(len(resample_bars(bars(90),3)),30)
    def test_resample_ohlc(self):
        result=resample_bars(bars(6),3)[0]
        self.assertIn("high",result)
    def test_consensus_bull(self):
        frames=[{"frame_name":"A","regime":{"primary_regime":"BULL","volatility_regime":"LOW_VOLATILITY","risk_mode":"RISK_ON"}}]*3
        self.assertEqual(build_consensus(frames,{"A":1})["primary_regime"],"BULL")
    def test_conflict(self):
        frames=[
            {"frame_name":"A","regime":{"primary_regime":"BULL","volatility_regime":"LOW_VOLATILITY","risk_mode":"RISK_ON"}},
            {"frame_name":"B","regime":{"primary_regime":"BEAR","volatility_regime":"HIGH_VOLATILITY","risk_mode":"RISK_OFF"}},
            {"frame_name":"C","regime":{"primary_regime":"SIDEWAYS","volatility_regime":"NORMAL_VOLATILITY","risk_mode":"RISK_ON"}},
        ]
        self.assertTrue(build_consensus(frames,{"A":1,"B":1,"C":1})["conflict_detected"])
    def test_multiplier(self):
        value=position_multiplier({"conflict_detected":True,"risk_mode":"RISK_OFF","volatility_regime":"HIGH_VOLATILITY","alignment_pct":33},1)
        self.assertLess(value,1)
    def test_recommend(self):
        self.assertEqual(recommend_strategies({"primary_regime":"BULL"},["MOMENTUM","RSI"])[0],"MOMENTUM")
    def test_missing_data(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],"MULTI_TIMEFRAME_HISTORICAL_DATA_REQUIRED")
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__": unittest.main()
