import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_candidate_backtest_v73_1 import (
    BacktestError,
    Bar,
    SCHEMA_VERSION,
    VERSION,
    build_backtest_report,
    calculate_metrics,
    canonical_json,
    entry_signal,
    load_ohlcv_csv,
    main,
    run_candidate_backtest,
)


def candidate(cid="CAND-TEST", rank=1):
    return {
        "candidate_id": cid,
        "rank": rank,
        "parameters": {
            "signal_threshold": 0.60,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.04,
            "min_volume_ratio": 1.00,
            "cooldown_bars": 2,
        },
        "evaluation_state": "PENDING_BACKTEST",
        "approved_for_live": False,
    }


def plan():
    return {
        "status": "PASS",
        "decision": "parameter_optimization_plan_created",
        "optimization_state": "CANDIDATES_READY",
        "champion_strategy": "breakout",
        "revision_id": "REV-breakout-V72",
        "candidates": [candidate("CAND-A", 1), candidate("CAND-B", 2)],
        "approved_for_live": False,
        "network_used": False,
        "parameter_optimization_report_sha256": "a" * 64,
        "schema_version": "v73.0.parameter_optimization.1",
        "version": "73.0",
    }


def bars(count=100):
    output = []
    price = 100.0
    for i in range(count):
        cycle = (i % 25) / 25
        drift = 0.35 if i % 40 < 24 else -0.18
        price = max(10.0, price + drift + (cycle - 0.5) * 0.08)
        output.append(Bar(
            timestamp=f"2026-01-{i+1:03d}",
            open=price - 0.1,
            high=price + 1.2,
            low=price - 0.8,
            close=price,
            volume=1000 + (400 if i % 7 == 0 else 0) + i,
        ))
    return output


class TestV731(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "73.1")

    def test_schema(self):
        self.assertEqual(SCHEMA_VERSION, "v73.1.offline_candidate_backtest.1")

    def test_metrics_empty(self):
        result = calculate_metrics([])
        self.assertEqual(result["trade_count"], 0)
        self.assertEqual(result["expectancy"], 0.0)

    def test_metrics_values(self):
        result = calculate_metrics([{"pnl": 10}, {"pnl": -5}, {"pnl": 0}])
        self.assertEqual(result["net_pnl"], 5.0)
        self.assertEqual(result["profit_factor"], 2.0)

    def test_entry_before_lookback_false(self):
        self.assertFalse(entry_signal(bars(), 5, candidate()["parameters"], 20))

    def test_candidate_completes(self):
        result = run_candidate_backtest(bars(), candidate())
        self.assertEqual(result["evaluation_state"], "BACKTEST_COMPLETED")

    def test_candidate_live_false(self):
        result = run_candidate_backtest(bars(), candidate())
        self.assertFalse(result["approved_for_live"])

    def test_candidate_has_metrics(self):
        result = run_candidate_backtest(bars(), candidate())
        self.assertIn("expectancy", result["metrics"])

    def test_report_pass(self):
        result = build_backtest_report(
            plan(), bars(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["status"], "PASS")

    def test_report_count(self):
        result = build_backtest_report(
            plan(), bars(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["candidate_count"], 2)

    def test_candidate_limit(self):
        result = build_backtest_report(
            plan(), bars(), candidate_limit=1,
            created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["candidate_count"], 1)

    def test_rank_present(self):
        result = build_backtest_report(
            plan(), bars(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["candidate_results"][0]["backtest_rank"], 1)

    def test_report_network_false(self):
        result = build_backtest_report(
            plan(), bars(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["network_used"])

    def test_report_live_false(self):
        result = build_backtest_report(
            plan(), bars(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["approved_for_live"])

    def test_requires_gate(self):
        result = build_backtest_report(
            plan(), bars(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertTrue(result["requires_quality_gate"])

    def test_deterministic(self):
        a = build_backtest_report(
            plan(), bars(), created_at="2026-07-30T00:00:00+00:00"
        )
        b = build_backtest_report(
            plan(), bars(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(a, b)

    def test_hash(self):
        result = build_backtest_report(
            plan(), bars(), created_at="2026-07-30T00:00:00+00:00"
        )
        copied = dict(result)
        observed = copied.pop("offline_candidate_backtest_report_sha256")
        expected = hashlib.sha256(canonical_json(copied).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_bad_plan_status(self):
        bad = plan()
        bad["status"] = "FAIL"
        with self.assertRaises(BacktestError):
            build_backtest_report(bad, bars())

    def test_bad_plan_schema(self):
        bad = plan()
        bad["schema_version"] = "bad"
        with self.assertRaises(BacktestError):
            build_backtest_report(bad, bars())

    def test_bad_plan_network(self):
        bad = plan()
        bad["network_used"] = True
        with self.assertRaises(BacktestError):
            build_backtest_report(bad, bars())

    def test_bad_candidate_limit(self):
        with self.assertRaises(BacktestError):
            build_backtest_report(plan(), bars(), candidate_limit=0)

    def test_bad_lookback(self):
        with self.assertRaises(BacktestError):
            run_candidate_backtest(bars(), candidate(), lookback=1)

    def test_bad_capital(self):
        with self.assertRaises(BacktestError):
            run_candidate_backtest(bars(), candidate(), initial_capital=0)

    def test_bad_risk(self):
        with self.assertRaises(BacktestError):
            run_candidate_backtest(bars(), candidate(), risk_fraction=0.5)

    def test_missing_parameter(self):
        bad = candidate()
        bad["parameters"].pop("stop_loss_pct")
        with self.assertRaises(BacktestError):
            run_candidate_backtest(bars(), bad)

    def test_load_csv(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "data.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp","open","high","low","close","volume"])
                for i, bar in enumerate(bars(35)):
                    writer.writerow([
                        f"{i:03d}", bar.open, bar.high, bar.low, bar.close, bar.volume
                    ])
            loaded = load_ohlcv_csv(path)
            self.assertEqual(len(loaded), 35)

    def test_csv_too_short(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "data.csv"
            path.write_text(
                "timestamp,open,high,low,close,volume\n"
                "001,1,1,1,1,1\n",
                encoding="utf-8",
            )
            with self.assertRaises(BacktestError):
                load_ohlcv_csv(path)

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan_path = root / "plan.json"
            data_path = root / "data.csv"
            output_path = root / "out.json"
            plan_path.write_text(json.dumps(plan()), encoding="utf-8")
            with data_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp","open","high","low","close","volume"])
                for i, bar in enumerate(bars(60)):
                    writer.writerow([
                        f"{i:03d}", bar.open, bar.high, bar.low, bar.close, bar.volume
                    ])
            code = main([
                "--plan", str(plan_path),
                "--data", str(data_path),
                "--output", str(output_path),
                "--candidate-limit", "1",
            ])
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main([
                "--plan", str(root / "missing.json"),
                "--data", str(root / "missing.csv"),
                "--output", str(root / "out.json"),
            ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
