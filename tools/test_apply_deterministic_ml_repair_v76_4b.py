import tempfile
import unittest
from pathlib import Path

from tools.apply_deterministic_ml_repair_v76_4b import apply


PREDICTOR = '''import math
from dataclasses import dataclass
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit

@dataclass
class MLPrediction:
    value: int

def create_model():
    return RandomForestClassifier(
        random_state=42,
        n_jobs=-1,
    )

def predict_stock_direction(
    symbol: str,
    data,
) -> MLPrediction:
    symbol = str(symbol)
    return MLPrediction(1)
'''

MARKET = '''import pandas as pd
import yfinance as yf

def get_history(symbol, period="5y", interval="1d"):
    data = yf.download(
        tickers=symbol,
        period=period,
        interval=interval,
        progress=False,
    )
    data.index.name = "Date"
    return data
'''

TEST_ML = '''from data.market import get_history
from ml.predictor import predict_stock_direction
symbol = "AAPL"
data = get_history(symbol=symbol, period="5y", interval="1d")
prediction = predict_stock_direction(symbol=symbol, data=data)
print(prediction)
'''


class TestV764B(unittest.TestCase):
    def create_repo(self, root: Path):
        (root / "ml").mkdir(parents=True)
        (root / "data").mkdir(parents=True)
        (root / "ml" / "predictor.py").write_text(PREDICTOR, encoding="utf-8")
        (root / "data" / "market.py").write_text(MARKET, encoding="utf-8")
        (root / "test_ml.py").write_text(TEST_ML, encoding="utf-8")

    def test_patch_all_three_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.create_repo(root)
            result = apply(root)
            self.assertEqual(result["status"], "PATCHED")
            predictor = (root / "ml" / "predictor.py").read_text(encoding="utf-8")
            market = (root / "data" / "market.py").read_text(encoding="utf-8")
            test_ml = (root / "test_ml.py").read_text(encoding="utf-8")
            self.assertIn("MODEL_N_JOBS = 1", predictor)
            self.assertIn("random.seed(MODEL_RANDOM_SEED)", predictor)
            self.assertNotIn("n_jobs=-1", predictor)
            self.assertIn("threads=False", market)
            self.assertIn("sort_index()", market)
            self.assertIn("AAPL_5y_1d_v76_4b.csv", test_ml)

    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.create_repo(root)
            apply(root)
            first = {p: (root / p).read_bytes() for p in ("ml/predictor.py", "data/market.py", "test_ml.py")}
            result = apply(root)
            second = {p: (root / p).read_bytes() for p in ("ml/predictor.py", "data/market.py", "test_ml.py")}
            self.assertEqual(result["status"], "ALREADY_PATCHED")
            self.assertEqual(first, second)

    def test_backups_created(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.create_repo(root)
            apply(root)
            self.assertTrue((root / "ml/predictor.py.v76_4b_backup").exists())
            self.assertTrue((root / "data/market.py.v76_4b_backup").exists())
            self.assertTrue((root / "test_ml.py.v76_4b_backup").exists())


if __name__ == "__main__":
    unittest.main()
