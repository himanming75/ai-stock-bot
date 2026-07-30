import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from tools.walk_forward_validation_v70_0 import (
    VERSION,
    SCHEMA_VERSION,
    WalkForwardError,
    build_validation,
    canonical_json,
    main,
    metrics,
    split_windows,
)


def trade(i, pnl, strategy="breakout"):
    return {
        "trade_id": f"T-{i:04d}",
        "strategy": strategy,
        "symbol": "AAPL",
        "realized_pnl": str(pnl),
        "opened_at": f"2026-01-{(i % 28) + 1:02d}T10:00:00Z",
        "closed_at": f"2026-01-{(i % 28) + 1:02d}T11:00:00Z",
        "holding_minutes": 60,
        "status": "CLOSED",
        "network_used": False,
    }


def report(count=100, strategy="breakout", pattern=None):
    if pattern is None:
        pattern = ["20", "15", "-8", "12", "-5"]
    trades = [trade(i + 1, pattern[i % len(pattern)], strategy) for i in range(count)]
    return {
        "status": "PASS",
        "decision": "paper_trade_scenarios_generated",
        "scenario": "test",
        "strategy": strategy,
        "network_used": False,
        "approved_for_live": False,
        "trade_count": count,
        "closed_trade_count": count,
        "open_trade_count": 0,
        "trades": trades,
        "schema_version": "v67.0.paper_trade_scenarios.1",
        "version": "67.0",
        "scenario_report_sha256": "a" * 64,
    }


class TestV70(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "70.0")

    def test_schema(self):
        self.assertEqual(SCHEMA_VERSION, "v70.0.walk_forward_validation.1")

    def test_metrics(self):
        m = metrics([trade(1, 10), trade(2, -5)], "x")
        self.assertEqual(m["net_pnl"], "5.0000")
        self.assertEqual(m["win_rate"], "0.500000")

    def test_window_count(self):
        windows = split_windows(report()["trades"], 50, 20, 10)
        self.assertEqual(len(windows), 4)

    def test_approved(self):
        r = build_validation(report())
        self.assertEqual(r["validation_state"], "APPROVED")

    def test_rejected(self):
        bad = report(pattern=["-10", "-5", "2", "-8", "1"])
        r = build_validation(bad)
        self.assertEqual(r["validation_state"], "REJECTED")

    def test_champion_detected(self):
        r = build_validation(report())
        self.assertEqual(r["champion_strategy"], "breakout")

    def test_explicit_champion(self):
        r = build_validation(report(strategy="momentum"), champion_strategy="momentum")
        self.assertEqual(r["champion_strategy"], "momentum")

    def test_multiple_requires_name(self):
        r = report()
        r["trades"][0]["strategy"] = "momentum"
        with self.assertRaises(WalkForwardError):
            build_validation(r)

    def test_missing_strategy(self):
        with self.assertRaises(WalkForwardError):
            build_validation(report(), champion_strategy="missing")

    def test_live_false(self):
        self.assertFalse(build_validation(report())["approved_for_live"])

    def test_network_false(self):
        self.assertFalse(build_validation(report())["network_used"])

    def test_monte_carlo_required_when_approved(self):
        self.assertTrue(build_validation(report())["requires_monte_carlo_validation"])

    def test_not_enough_trades(self):
        with self.assertRaises(WalkForwardError):
            build_validation(report(count=20), train_size=15, forward_size=10)

    def test_invalid_train_size(self):
        with self.assertRaises(WalkForwardError):
            build_validation(report(), train_size=0)

    def test_invalid_forward_size(self):
        with self.assertRaises(WalkForwardError):
            build_validation(report(), forward_size=0)

    def test_invalid_step_size(self):
        with self.assertRaises(WalkForwardError):
            build_validation(report(), step_size=0)

    def test_bad_status(self):
        r = report()
        r["status"] = "FAIL"
        with self.assertRaises(WalkForwardError):
            build_validation(r)

    def test_bad_schema(self):
        r = report()
        r["schema_version"] = "bad"
        with self.assertRaises(WalkForwardError):
            build_validation(r)

    def test_bad_network(self):
        r = report()
        r["network_used"] = True
        with self.assertRaises(WalkForwardError):
            build_validation(r)

    def test_bad_live(self):
        r = report()
        r["approved_for_live"] = True
        with self.assertRaises(WalkForwardError):
            build_validation(r)

    def test_bad_count(self):
        r = report()
        r["trade_count"] = 99
        with self.assertRaises(WalkForwardError):
            build_validation(r)

    def test_hash(self):
        r = build_validation(report())
        c = dict(r)
        observed = c.pop("walk_forward_report_sha256")
        expected = hashlib.sha256(canonical_json(c).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_deterministic(self):
        self.assertEqual(build_validation(report()), build_validation(report()))

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "input.json"
            out = root / "output.json"
            inp.write_text(json.dumps(report()), encoding="utf-8")
            code = main([
                "--input", str(inp),
                "--champion-strategy", "breakout",
                "--output", str(out),
            ])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main([
                "--input", str(root / "missing.json"),
                "--output", str(root / "output.json"),
            ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
