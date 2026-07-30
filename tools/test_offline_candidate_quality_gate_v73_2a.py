import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_candidate_quality_gate_v73_2a import (
    DEFAULT_THRESHOLDS,
    QualityGateError,
    SCHEMA_VERSION,
    VERSION,
    build_quality_gate_report,
    canonical_json,
    evaluate_candidate,
    main,
    quality_reasons,
)


def candidate(cid, rank, trades, win_rate, pf, expectancy, net_pnl):
    return {
        "candidate_id": cid,
        "backtest_rank": rank,
        "parameters": {"x": rank},
        "metrics": {
            "trade_count": trades,
            "win_rate": win_rate,
            "profit_factor": pf,
            "expectancy": expectancy,
            "net_pnl": net_pnl,
        },
        "approved_for_live": False,
    }


def report():
    return {
        "status": "PASS",
        "decision": "offline_candidate_backtests_completed",
        "execution_state": "BACKTESTS_COMPLETED",
        "champion_strategy": "breakout",
        "revision_id": "REV-breakout-V72",
        "candidate_results": [
            candidate("CAND-A", 1, 10, 0.60, 2.0, 5.0, 50.0),
            candidate("CAND-B", 2, 3, 0.30, 0.8, -1.0, -3.0),
            candidate("CAND-C", 3, 8, 0.50, None, 2.0, 16.0),
        ],
        "approved_for_live": False,
        "network_used": False,
        "offline_candidate_backtest_report_sha256": "a" * 64,
        "schema_version": "v73.1.offline_candidate_backtest.1",
        "version": "73.1",
    }


class TestV732A(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "73.2A")

    def test_schema(self):
        self.assertEqual(
            SCHEMA_VERSION,
            "v73.2a.offline_candidate_quality_gate.1"
        )

    def test_good_candidate_passes(self):
        item = evaluate_candidate(report()["candidate_results"][0], DEFAULT_THRESHOLDS)
        self.assertEqual(item["quality_gate_status"], "PASS")

    def test_bad_candidate_fails(self):
        item = evaluate_candidate(report()["candidate_results"][1], DEFAULT_THRESHOLDS)
        self.assertEqual(item["quality_gate_status"], "FAIL")

    def test_pf_none_allowed(self):
        item = evaluate_candidate(report()["candidate_results"][2], DEFAULT_THRESHOLDS)
        self.assertEqual(item["quality_gate_status"], "PASS")

    def test_failure_reasons(self):
        reasons = quality_reasons(
            report()["candidate_results"][1]["metrics"],
            DEFAULT_THRESHOLDS,
        )
        self.assertIn("INSUFFICIENT_TRADE_COUNT", reasons)
        self.assertIn("LOW_WIN_RATE", reasons)
        self.assertIn("LOW_PROFIT_FACTOR", reasons)
        self.assertIn("NON_POSITIVE_EXPECTANCY", reasons)
        self.assertIn("NON_POSITIVE_NET_PNL", reasons)

    def test_report_pass(self):
        result = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["status"], "PASS")

    def test_survivor_count(self):
        result = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["survivor_count"], 2)

    def test_failed_count(self):
        result = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["failed_count"], 1)

    def test_provisional_champion(self):
        result = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["provisional_champion_candidate_id"], "CAND-C")

    def test_rank_sequence(self):
        result = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(
            [x["quality_rank"] for x in result["candidate_evaluations"]],
            [1, 2, 3],
        )

    def test_live_false(self):
        result = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["approved_for_live"])

    def test_network_false(self):
        result = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["network_used"])

    def test_requires_requalification(self):
        result = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertTrue(result["requires_requalification"])

    def test_no_survivors(self):
        bad = report()
        bad["candidate_results"] = [bad["candidate_results"][1]]
        result = build_quality_gate_report(
            bad, created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["quality_gate_state"], "NO_SURVIVORS")
        self.assertFalse(result["requires_requalification"])

    def test_custom_threshold(self):
        result = build_quality_gate_report(
            report(),
            thresholds={"minimum_trade_count": 20},
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertEqual(result["survivor_count"], 0)

    def test_deterministic(self):
        a = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        b = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(a, b)

    def test_hash(self):
        result = build_quality_gate_report(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        copied = dict(result)
        observed = copied.pop("quality_gate_report_sha256")
        expected = hashlib.sha256(canonical_json(copied).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_bad_status(self):
        bad = report()
        bad["status"] = "FAIL"
        with self.assertRaises(QualityGateError):
            build_quality_gate_report(bad)

    def test_bad_schema(self):
        bad = report()
        bad["schema_version"] = "bad"
        with self.assertRaises(QualityGateError):
            build_quality_gate_report(bad)

    def test_bad_network(self):
        bad = report()
        bad["network_used"] = True
        with self.assertRaises(QualityGateError):
            build_quality_gate_report(bad)

    def test_bad_live(self):
        bad = report()
        bad["approved_for_live"] = True
        with self.assertRaises(QualityGateError):
            build_quality_gate_report(bad)

    def test_missing_results(self):
        bad = report()
        bad["candidate_results"] = []
        with self.assertRaises(QualityGateError):
            build_quality_gate_report(bad)

    def test_bad_threshold(self):
        with self.assertRaises(QualityGateError):
            build_quality_gate_report(
                report(),
                thresholds={"minimum_trade_count": 0},
            )

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "in.json"
            output_path = root / "out.json"
            input_path.write_text(json.dumps(report()), encoding="utf-8")
            code = main([
                "--input", str(input_path),
                "--output", str(output_path),
            ])
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main([
                "--input", str(root / "missing.json"),
                "--output", str(root / "out.json"),
            ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
