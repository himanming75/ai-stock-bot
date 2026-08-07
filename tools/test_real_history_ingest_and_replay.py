from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    def test_ingestion_contract_literals(self):
        p=Path("tools/ingest_alpaca_real_historical.py")
        txt=p.read_text(encoding="utf-8")
        self.assertIn("StockHistoricalDataClient",txt)
        self.assertIn("DataFeed.IEX",txt)
        self.assertIn('"broker_write_performed":False',txt)
        self.assertNotIn("TradingClient(",txt)
        self.assertNotIn("submit_order(",txt)

    def test_replay_reuses_existing_engine(self):
        p=Path("tools/run_existing_offline_engine_on_real_history.py")
        txt=p.read_text(encoding="utf-8")
        self.assertIn("from backtest.offline_multi_asset_v26_1 import",txt)
        self.assertIn("run_multi_asset_backtest",txt)
        self.assertIn('"strategy_equivalence_to_current_paper":"NOT_ASSERTED"',txt)
        self.assertNotIn("submit_order(",txt)

if __name__=="__main__":
    unittest.main()
