import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from tools.monte_carlo_robustness_validation_v71_0 import (
    VERSION,
    SCHEMA_VERSION,
    MonteCarloError,
    build_validation,
    canonical_json,
    drawdown_stats,
    main,
    percentile,
    run_simulations,
)


def walk_forward(approved=True):
    data = {
        "status": "PASS",
        "decision": (
            "walk_forward_validation_approved"
            if approved else "walk_forward_validation_rejected"
        ),
        "validation_state": "APPROVED" if approved else "REJECTED",
        "champion_strategy": "breakout",
        "requires_monte_carlo_validation": approved,
        "approved_for_live": False,
        "network_used": False,
        "schema_version": "v70.0.walk_forward_validation.1",
        "version": "70.0",
        "walk_forward_report_sha256": "a" * 64,
    }
    return data


def trade_report(pattern=None, count=100):
    if pattern is None:
        pattern = ["20", "15", "-2", "12", "-1"]
    trades = []
    for i in range(count):
        trades.append({
            "trade_id": f"T-{i:04d}",
            "strategy": "breakout",
            "realized_pnl": pattern[i % len(pattern)],
            "status": "CLOSED",
            "network_used": False,
        })
    return {
        "status": "PASS",
        "trade_count": count,
        "trades": trades,
        "network_used": False,
        "approved_for_live": False,
        "schema_version": "v67.0.paper_trade_scenarios.1",
        "scenario_report_sha256": "b" * 64,
    }


class TestV71(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "71.0")

    def test_schema(self):
        self.assertEqual(
            SCHEMA_VERSION,
            "v71.0.monte_carlo_robustness_validation.1",
        )

    def test_drawdown(self):
        s = drawdown_stats([
            Decimal("10"), Decimal("-4"), Decimal("-3"), Decimal("8")
        ])
        self.assertEqual(s["max_drawdown"], Decimal("7"))

    def test_percentile(self):
        values = [Decimal("1"), Decimal("2"), Decimal("3")]
        self.assertEqual(percentile(values, Decimal("0.5")), Decimal("2"))

    def test_simulation_count(self):
        sims = run_simulations(
            [Decimal("1"), Decimal("-1")], 100, 1
        )
        self.assertEqual(len(sims), 100)

    def test_minimum_simulations(self):
        with self.assertRaises(MonteCarloError):
            run_simulations([Decimal("1")], 99, 1)

    def test_blocked(self):
        result = build_validation(
            walk_forward(False), trade_report(), simulation_count=100
        )
        self.assertEqual(result["validation_state"], "BLOCKED")
        self.assertEqual(result["simulation_count"], 0)

    def test_blocked_requires_revision(self):
        result = build_validation(
            walk_forward(False), trade_report(), simulation_count=100
        )
        self.assertTrue(result["requires_strategy_revision"])

    def test_approved(self):
        result = build_validation(
            walk_forward(True), trade_report(), simulation_count=100
        )
        self.assertEqual(result["validation_state"], "APPROVED")

    def test_rejected(self):
        result = build_validation(
            walk_forward(True),
            trade_report(pattern=["3", "-10", "-8", "2"]),
            simulation_count=100,
        )
        self.assertEqual(result["validation_state"], "REJECTED")

    def test_deterministic(self):
        a = build_validation(
            walk_forward(True), trade_report(), simulation_count=100, seed=99
        )
        b = build_validation(
            walk_forward(True), trade_report(), simulation_count=100, seed=99
        )
        self.assertEqual(a, b)

    def test_seed_changes_drawdown(self):
        a = build_validation(
            walk_forward(True), trade_report(), simulation_count=100, seed=99
        )
        b = build_validation(
            walk_forward(True), trade_report(), simulation_count=100, seed=100
        )
        self.assertNotEqual(
            a["p95_max_drawdown"], b["p95_max_drawdown"]
        )

    def test_hash(self):
        r = build_validation(
            walk_forward(True), trade_report(), simulation_count=100
        )
        c = dict(r)
        observed = c.pop("monte_carlo_report_sha256")
        expected = hashlib.sha256(canonical_json(c).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_live_false(self):
        r = build_validation(
            walk_forward(True), trade_report(), simulation_count=100
        )
        self.assertFalse(r["approved_for_live"])

    def test_network_false(self):
        r = build_validation(
            walk_forward(True), trade_report(), simulation_count=100
        )
        self.assertFalse(r["network_used"])

    def test_bad_walk_schema(self):
        w = walk_forward(True)
        w["schema_version"] = "bad"
        with self.assertRaises(MonteCarloError):
            build_validation(w, trade_report(), simulation_count=100)

    def test_bad_walk_network(self):
        w = walk_forward(True)
        w["network_used"] = True
        with self.assertRaises(MonteCarloError):
            build_validation(w, trade_report(), simulation_count=100)

    def test_bad_trade_schema(self):
        t = trade_report()
        t["schema_version"] = "bad"
        with self.assertRaises(MonteCarloError):
            build_validation(walk_forward(True), t, simulation_count=100)

    def test_bad_trade_count(self):
        t = trade_report()
        t["trade_count"] = 99
        with self.assertRaises(MonteCarloError):
            build_validation(walk_forward(True), t, simulation_count=100)

    def test_missing_champion_trades(self):
        t = trade_report()
        for row in t["trades"]:
            row["strategy"] = "momentum"
        with self.assertRaises(MonteCarloError):
            build_validation(walk_forward(True), t, simulation_count=100)

    def test_profitable_rate(self):
        r = build_validation(
            walk_forward(True), trade_report(), simulation_count=100
        )
        self.assertEqual(r["profitable_simulation_rate"], "1.000000")

    def test_extended_paper_required(self):
        r = build_validation(
            walk_forward(True), trade_report(), simulation_count=100
        )
        self.assertTrue(r["requires_extended_paper_validation"])

    def test_main_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wf = root / "wf.json"
            tr = root / "tr.json"
            out = root / "out.json"
            wf.write_text(json.dumps(walk_forward(False)), encoding="utf-8")
            tr.write_text(json.dumps(trade_report()), encoding="utf-8")
            code = main([
                "--walk-forward", str(wf),
                "--paper-trades", str(tr),
                "--simulations", "100",
                "--output", str(out),
            ])
            self.assertEqual(code, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["validation_state"], "BLOCKED")

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wf = root / "wf.json"
            tr = root / "tr.json"
            out = root / "out.json"
            wf.write_text(json.dumps(walk_forward(True)), encoding="utf-8")
            tr.write_text(json.dumps(trade_report()), encoding="utf-8")
            code = main([
                "--walk-forward", str(wf),
                "--paper-trades", str(tr),
                "--simulations", "100",
                "--output", str(out),
            ])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main([
                "--walk-forward", str(root / "missing-wf.json"),
                "--paper-trades", str(root / "missing-trades.json"),
                "--output", str(root / "out.json"),
            ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
