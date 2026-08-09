
from pathlib import Path
import importlib.util
import tempfile
import json
import unittest

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load(Path("dashboard/market_regime_analysis_v3_16.py"),"v316")
        cls.analytics=Path("dashboard/trade_analytics_v3_5.py").read_text(encoding="utf-8")
        cls.html=Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def test_explicit_regime_extraction(self):
        record={"trade_id":"T1","context":{"market_regime":"bullish","volatility_regime":"high volatility"}}
        direction,volatility,evidence=self.m._extract_explicit_regime(record)
        self.assertEqual(direction,"BULL")
        self.assertEqual(volatility,"HIGH_VOL")
        self.assertTrue(evidence)

    def test_no_price_inference(self):
        record={"trade_id":"T1","entry_price":100,"exit_price":110}
        direction,volatility,evidence=self.m._extract_explicit_regime(record)
        self.assertIsNone(direction)
        self.assertIsNone(volatility)
        self.assertEqual(evidence,[])

    def test_discovery_links_trade_id(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            path=root/"runtime"/"paper_full_auto_lifecycle"/"closed_round_trips.jsonl"
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps({"trade_id":"T1","market_regime":"bear"})+"\n",encoding="utf-8")
            evidence,sources=self.m.discover_regime_evidence(root,[{"record_id":"T1","pnl":1.0}])
            self.assertEqual(evidence["T1"]["direction_regime"],"BEAR")
            self.assertTrue(sources)

    def test_api_exposed(self):
        self.assertIn('"market_regime_analysis": regime_analysis',self.analytics)

    def test_ui_and_safety(self):
        self.assertIn('id="regimeSection"',self.html)
        self.assertIn("Market Regime Performance Analysis / 시장 환경별 전략 성과 분석",self.html)
        combined=Path("dashboard/market_regime_analysis_v3_16.py").read_text(encoding="utf-8")+self.analytics+self.html
        for bad in ("TradingClient(","submit_order(","MarketOrderRequest("):
            self.assertNotIn(bad,combined)

if __name__=="__main__":
    unittest.main()
