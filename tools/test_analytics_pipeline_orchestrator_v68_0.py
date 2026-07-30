import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.analytics_pipeline_orchestrator_v68_0 import (
    VERSION, SCHEMA_VERSION, PipelineError, build_pipeline,
    canonical_json, main, run, validate_v67
)


def trade(i, pnl, strategy="balanced_signal", symbol="AAPL"):
    return {
        "trade_id": f"V67-{i:06d}",
        "strategy": strategy,
        "symbol": symbol,
        "side": "LONG",
        "quantity": 10,
        "entry_price": "100.0000",
        "exit_price": "101.0000",
        "realized_pnl": str(pnl),
        "return_pct": "1.000000",
        "opened_at": "2026-01-01T00:00:00Z",
        "closed_at": "2026-01-01T01:00:00Z",
        "holding_minutes": 60,
        "exit_reason": "TAKE_PROFIT" if float(pnl) > 0 else "STOP_LOSS",
        "status": "CLOSED",
        "network_used": False,
        "trade_sha256": "a" * 64,
    }


def sample_v67(wins=60, losses=40):
    trades = [trade(i + 1, "20") for i in range(wins)]
    trades += [trade(wins + i + 1, "-10") for i in range(losses)]
    report = {
        "status": "PASS",
        "decision": "paper_trade_scenarios_generated",
        "scenario": "mixed",
        "seed": 6700,
        "network_used": False,
        "approved_for_live": False,
        "trade_count": len(trades),
        "closed_trade_count": len(trades),
        "open_trade_count": 0,
        "symbols": ["AAPL"],
        "summary": {},
        "trades": trades,
        "schema_version": "v67.0.paper_trade_scenarios.1",
        "version": "67.0",
        "scenario_report_sha256": "b" * 64,
    }
    return report


class TestV68(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "68.0")

    def test_schema(self):
        self.assertEqual(SCHEMA_VERSION, "v68.0.analytics_pipeline_orchestrator.1")

    def test_pass(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["status"], "PASS")

    def test_pipeline_pass(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["pipeline_status"], "PASS")

    def test_trade_count(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["trade_count"], 100)

    def test_all_closed(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["closed_trade_count"], 100)
        self.assertEqual(r["open_trade_count"], 0)

    def test_win_rate(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["analytics"]["overall"]["win_rate"], "0.600000")

    def test_net_pnl(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["analytics"]["overall"]["net_pnl"], "800.0000")

    def test_profit_factor(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["analytics"]["overall"]["profit_factor"], "3.000000")

    def test_expectancy(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["analytics"]["overall"]["expectancy"], "8.0000")

    def test_approve(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["quality_gate"]["quality_gate"], "APPROVE")

    def test_promotion(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(r["promotion"]["promotion_state"], "EXTENDED_PAPER_APPROVED")

    def test_never_live(self):
        r = build_pipeline(sample_v67())
        self.assertFalse(r["approved_for_live"])
        self.assertFalse(r["quality_gate"]["approved_for_live"])
        self.assertFalse(r["promotion"]["approved_for_live"])

    def test_network_false(self):
        r = build_pipeline(sample_v67())
        self.assertFalse(r["network_used"])

    def test_insufficient(self):
        r = build_pipeline(sample_v67(5, 5), minimum_trades=20)
        self.assertEqual(r["quality_gate"]["quality_gate"], "INSUFFICIENT_DATA")

    def test_reject(self):
        r = build_pipeline(sample_v67(2, 98))
        self.assertEqual(r["quality_gate"]["quality_gate"], "REJECT")

    def test_strategy_group(self):
        data = sample_v67(2, 0)
        data["trades"][1]["strategy"] = "other"
        r = build_pipeline(data)
        self.assertEqual(len(r["analytics"]["by_strategy"]), 2)

    def test_symbol_group(self):
        data = sample_v67(2, 0)
        data["trades"][1]["symbol"] = "MSFT"
        r = build_pipeline(data)
        self.assertEqual(len(r["analytics"]["by_symbol"]), 2)

    def test_ranking(self):
        data = sample_v67(2, 0)
        data["trades"][1]["strategy"] = "other"
        data["trades"][1]["realized_pnl"] = "30"
        r = build_pipeline(data)
        self.assertEqual(r["analytics"]["strategy_ranking"][0]["strategy"], "other")

    def test_hash_length(self):
        r = build_pipeline(sample_v67())
        self.assertEqual(len(r["pipeline_report_sha256"]), 64)

    def test_hash_matches(self):
        r = build_pipeline(sample_v67())
        copy_r = dict(r)
        observed = copy_r.pop("pipeline_report_sha256")
        expected = hashlib.sha256(canonical_json(copy_r).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_deterministic(self):
        self.assertEqual(build_pipeline(sample_v67()), build_pipeline(sample_v67()))

    def test_bad_status(self):
        d = sample_v67()
        d["status"] = "FAIL"
        with self.assertRaises(PipelineError):
            build_pipeline(d)

    def test_bad_network(self):
        d = sample_v67()
        d["network_used"] = True
        with self.assertRaises(PipelineError):
            build_pipeline(d)

    def test_bad_live(self):
        d = sample_v67()
        d["approved_for_live"] = True
        with self.assertRaises(PipelineError):
            build_pipeline(d)

    def test_bad_schema(self):
        d = sample_v67()
        d["schema_version"] = "bad"
        with self.assertRaises(PipelineError):
            build_pipeline(d)

    def test_bad_count(self):
        d = sample_v67()
        d["trade_count"] = 99
        with self.assertRaises(PipelineError):
            build_pipeline(d)

    def test_open_trade_forbidden(self):
        d = sample_v67()
        d["open_trade_count"] = 1
        with self.assertRaises(PipelineError):
            build_pipeline(d)

    def test_trade_must_be_closed(self):
        d = sample_v67()
        d["trades"][0]["status"] = "OPEN"
        with self.assertRaises(PipelineError):
            build_pipeline(d)

    def test_trade_network_false(self):
        d = sample_v67()
        d["trades"][0]["network_used"] = True
        with self.assertRaises(PipelineError):
            build_pipeline(d)

    def test_run_writes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "v67.json"
            out = root / "v68.json"
            inp.write_text(json.dumps(sample_v67()), encoding="utf-8")
            r = run(inp, out)
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text()), r)

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "v67.json"
            out = root / "v68.json"
            inp.write_text(json.dumps(sample_v67()), encoding="utf-8")
            self.assertEqual(main(["--paper-trades", str(inp), "--output", str(out)]), 0)

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertEqual(main([
                "--paper-trades", str(root / "missing.json"),
                "--output", str(root / "out.json")
            ]), 1)


if __name__ == "__main__":
    unittest.main()
