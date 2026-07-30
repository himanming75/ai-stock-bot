import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.candidate_requalification_pipeline_v74_0 import (
    DEFAULT_CONFIG,
    RequalificationError,
    SCHEMA_VERSION,
    VERSION,
    build_pipeline_report,
    canonical_json,
    evaluate_monte_carlo,
    evaluate_walk_forward,
    main,
    metrics_from_pnls,
)


def trades(values):
    return [
        {
            "entry_timestamp": f"E{i}",
            "exit_timestamp": f"X{i}",
            "pnl": value,
        }
        for i, value in enumerate(values)
    ]


def candidate_result(cid, rank, pnls):
    metrics = metrics_from_pnls(pnls)
    return {
        "candidate_id": cid,
        "backtest_rank": rank,
        "parameters": {"p": rank},
        "metrics": metrics,
        "trades": trades(pnls),
        "approved_for_live": False,
    }


def manifest():
    return {
        "status": "PASS",
        "decision": "requalification_manifest_created",
        "manifest_state": "READY_FOR_REQUALIFICATION",
        "champion_strategy": "breakout",
        "revision_id": "REV-breakout-V72",
        "selected_candidates": [
            {
                "candidate_id": "CAND-A",
                "requalification_priority": 1,
                "parameters": {"p": 1},
            },
            {
                "candidate_id": "CAND-B",
                "requalification_priority": 2,
                "parameters": {"p": 2},
            },
        ],
        "approved_for_live": False,
        "network_used": False,
        "requalification_manifest_sha256": "a" * 64,
        "schema_version": "v73.2b.survivor_requalification_manifest.1",
        "version": "73.2B",
    }


def backtest():
    return {
        "status": "PASS",
        "decision": "offline_candidate_backtests_completed",
        "execution_state": "BACKTESTS_COMPLETED",
        "candidate_results": [
            candidate_result("CAND-A", 1, [10, 8, 7, 9, 6, 5]),
            candidate_result("CAND-B", 2, [10, -20, 5, -8, 2, -4]),
        ],
        "approved_for_live": False,
        "network_used": False,
        "offline_candidate_backtest_report_sha256": "b" * 64,
        "schema_version": "v73.1.offline_candidate_backtest.1",
        "version": "73.1",
    }


class TestV74(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "74.0")

    def test_schema(self):
        self.assertEqual(
            SCHEMA_VERSION,
            "v74.candidate_requalification_pipeline.1",
        )

    def test_metrics(self):
        result = metrics_from_pnls([10, -5])
        self.assertEqual(result["net_pnl"], 5.0)
        self.assertEqual(result["profit_factor"], 2.0)

    def test_walk_forward_pass(self):
        result = evaluate_walk_forward(
            [10, 8, 7, 9, 6, 5],
            DEFAULT_CONFIG["walk_forward"],
        )
        self.assertEqual(result["status"], "PASS")

    def test_walk_forward_reject(self):
        result = evaluate_walk_forward(
            [10, -20, 5, -8, 2, -4],
            DEFAULT_CONFIG["walk_forward"],
        )
        self.assertEqual(result["status"], "FAIL")

    def test_monte_carlo_deterministic(self):
        a = evaluate_monte_carlo(
            "CAND-A", [10, 8, 7, 9, 6, 5],
            DEFAULT_CONFIG["monte_carlo"],
        )
        b = evaluate_monte_carlo(
            "CAND-A", [10, 8, 7, 9, 6, 5],
            DEFAULT_CONFIG["monte_carlo"],
        )
        self.assertEqual(a, b)

    def test_report_pass(self):
        result = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertEqual(result["status"], "PASS")

    def test_one_approved(self):
        result = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertEqual(result["approved_candidate_count"], 1)

    def test_champion(self):
        result = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertEqual(result["champion_candidate_id"], "CAND-A")

    def test_second_rejected(self):
        result = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        rejected = [
            x for x in result["execution_results"]
            if x["candidate_id"] == "CAND-B"
        ][0]
        self.assertEqual(rejected["requalification_state"], "REJECTED")

    def test_stage_sequence(self):
        result = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        stages = result["execution_results"][0]["stage_results"]
        self.assertEqual([x["stage"] for x in stages], ["V68", "V70", "V71"])

    def test_live_false(self):
        result = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertFalse(result["approved_for_live"])

    def test_network_false(self):
        result = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertFalse(result["network_used"])

    def test_deterministic(self):
        a = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        b = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertEqual(a, b)

    def test_hash(self):
        result = build_pipeline_report(
            manifest(), backtest(),
            created_at="2026-07-30T00:00:00+00:00",
        )
        copied = dict(result)
        observed = copied.pop("candidate_requalification_report_sha256")
        expected = hashlib.sha256(canonical_json(copied).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_bad_manifest_status(self):
        bad = manifest()
        bad["status"] = "FAIL"
        with self.assertRaises(RequalificationError):
            build_pipeline_report(bad, backtest())

    def test_bad_manifest_schema(self):
        bad = manifest()
        bad["schema_version"] = "bad"
        with self.assertRaises(RequalificationError):
            build_pipeline_report(bad, backtest())

    def test_bad_manifest_network(self):
        bad = manifest()
        bad["network_used"] = True
        with self.assertRaises(RequalificationError):
            build_pipeline_report(bad, backtest())

    def test_bad_backtest_status(self):
        bad = backtest()
        bad["status"] = "FAIL"
        with self.assertRaises(RequalificationError):
            build_pipeline_report(manifest(), bad)

    def test_bad_backtest_schema(self):
        bad = backtest()
        bad["schema_version"] = "bad"
        with self.assertRaises(RequalificationError):
            build_pipeline_report(manifest(), bad)

    def test_missing_candidate(self):
        bad = backtest()
        bad["candidate_results"] = [bad["candidate_results"][0]]
        with self.assertRaises(RequalificationError):
            build_pipeline_report(manifest(), bad)

    def test_bad_window_count(self):
        with self.assertRaises(RequalificationError):
            build_pipeline_report(
                manifest(), backtest(),
                config={"walk_forward": {"window_count": 1}},
            )

    def test_bad_simulation_count(self):
        with self.assertRaises(RequalificationError):
            build_pipeline_report(
                manifest(), backtest(),
                config={"monte_carlo": {"simulation_count": 10}},
            )

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = root / "manifest.json"
            b = root / "backtest.json"
            o = root / "out.json"
            m.write_text(json.dumps(manifest()), encoding="utf-8")
            b.write_text(json.dumps(backtest()), encoding="utf-8")
            code = main([
                "--manifest", str(m),
                "--backtest", str(b),
                "--output", str(o),
            ])
            self.assertEqual(code, 0)
            self.assertTrue(o.exists())

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main([
                "--manifest", str(root / "missing.json"),
                "--backtest", str(root / "missing2.json"),
                "--output", str(root / "out.json"),
            ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
