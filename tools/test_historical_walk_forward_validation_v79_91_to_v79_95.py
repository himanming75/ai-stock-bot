from pathlib import Path
from tempfile import TemporaryDirectory
import json, unittest
from alpaca_market_data.historical_walk_forward_validation_v79_91_95 import *

def curve(count=11):
    return [
        {"index": i, "timestamp": f"{i:02d}", "equity": 100.0 + i}
        for i in range(count)
    ]

class Tests(unittest.TestCase):
    def setUp(self):
        self.config = WalkForwardConfig()

    def test_config(self):
        self.config.validate()

    def test_network_rejected(self):
        with self.assertRaises(ValueError):
            WalkForwardConfig(allow_network=True).validate()

    def test_window_plan(self):
        windows = plan_walk_forward_windows(curve(), self.config)
        self.assertEqual(len(windows), 3)

    def test_no_leakage(self):
        windows = plan_walk_forward_windows(curve(), self.config)
        stats = validate_windows(windows)
        self.assertEqual(stats["leakage_count"], 0)

    def test_insufficient_folds(self):
        with self.assertRaises(ValueError):
            plan_walk_forward_windows(curve(5), self.config)

    def test_fold_execution(self):
        windows = plan_walk_forward_windows(curve(), self.config)
        folds = execute_folds(curve(), windows)
        self.assertEqual(len(folds), 3)
        self.assertTrue(all(fold["status"] == "PASS" for fold in folds))

    def test_aggregate(self):
        windows = plan_walk_forward_windows(curve(), self.config)
        folds = execute_folds(curve(), windows)
        result = aggregate_fold_results(folds, self.config)
        self.assertEqual(result["status"], "PASS")

    def test_drawdown_violation(self):
        folds = [{
            "test_metrics": {
                "total_return": -0.5,
                "sharpe_ratio": -1.0,
                "max_drawdown_pct": 0.5,
            }
        }, {
            "test_metrics": {
                "total_return": -0.4,
                "sharpe_ratio": -1.0,
                "max_drawdown_pct": 0.4,
            }
        }]
        result = aggregate_fold_results(folds, self.config)
        self.assertEqual(result["status"], "FAIL")

    def test_out_of_order_curve(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "portfolio.json"
            path.write_text(json.dumps({
                "snapshots": [
                    {"timestamp": "2", "equity": 100},
                    {"timestamp": "1", "equity": 100},
                ]
            }))
            with self.assertRaises(ValueError):
                load_equity_curve(path)

    def test_store_reuse(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.json"
            source.write_text("{}")
            windows = plan_walk_forward_windows(curve(), self.config)
            folds = execute_folds(curve(), windows)
            aggregate = aggregate_fold_results(folds, self.config)
            store_walk_forward(root / "output", source, windows, folds, aggregate)
            second = store_walk_forward(
                root / "output", source, windows, folds, aggregate
            )
            self.assertTrue(second["reused_existing_validation"])

    def test_manifest(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.json"
            source.write_text("{}")
            windows = plan_walk_forward_windows(curve(), self.config)
            folds = execute_folds(curve(), windows)
            aggregate = aggregate_fold_results(folds, self.config)
            stored = store_walk_forward(
                root / "output", source, windows, folds, aggregate
            )
            self.assertTrue(
                verify_walk_forward_manifest(
                    root / "output", stored["manifest"]
                )
            )

    def test_manifest_tamper(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.json"
            source.write_text("{}")
            windows = plan_walk_forward_windows(curve(), self.config)
            folds = execute_folds(curve(), windows)
            aggregate = aggregate_fold_results(folds, self.config)
            stored = store_walk_forward(
                root / "output", source, windows, folds, aggregate
            )
            (root / "output/walk_forward_fold_ledger.json").write_text("{}")
            with self.assertRaises(ValueError):
                verify_walk_forward_manifest(
                    root / "output", stored["manifest"]
                )

    def test_bad_certificate(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "certificate.json"
            path.write_text("{}")
            with self.assertRaises(ValueError):
                validate_performance_certificate(path)

    def test_segment_metrics(self):
        metrics = segment_metrics(curve(4))
        self.assertGreater(metrics["total_return"], 0)
        self.assertGreaterEqual(metrics["max_drawdown_pct"], 0)

    def test_safety_source(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "alpaca_market_data/historical_walk_forward_validation_v79_91_95.py"
        ).read_text().lower()
        self.assertNotIn("submit_order(", source)
        self.assertNotIn("tradingclient(", source)
        self.assertNotIn("api_secret", source)

if __name__ == "__main__":
    unittest.main()
