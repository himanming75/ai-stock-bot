import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.parameter_optimization_v73_0 import (
    OptimizationError,
    SCHEMA_VERSION,
    VERSION,
    build_optimization_plan,
    build_search_space,
    canonical_json,
    candidate_id,
    main,
)


def sample_v72():
    return {
        "status": "PASS",
        "decision": "strategy_revision_required",
        "requalification_state": "REVISION_REQUIRED",
        "revision_id": "REV-breakout-V72",
        "champion_strategy": "breakout",
        "requires_strategy_revision": True,
        "recommendations": [
            {"code": "REV-EDGE-RECOVERY"},
            {"code": "REV-REQUALIFICATION"},
            {"code": "REV-ENTRY-QUALITY"},
            {"code": "REV-LOSS-CONTROL"},
            {"code": "REV-ROBUSTNESS"},
        ],
        "approved_for_live": False,
        "network_used": False,
        "strategy_revision_report_sha256": "a" * 64,
        "schema_version": "v72.0.strategy_revision_requalification.1",
        "version": "72.0",
    }


def baseline():
    return {
        "signal_threshold": 0.60,
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.04,
        "min_volume_ratio": 1.00,
        "cooldown_bars": 2,
    }


class TestV73(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "73.0")

    def test_schema(self):
        self.assertEqual(SCHEMA_VERSION, "v73.0.parameter_optimization.1")

    def test_search_space_signal(self):
        space = build_search_space(sample_v72(), baseline())
        self.assertEqual(space["signal_threshold"], [0.6, 0.65, 0.7])

    def test_search_space_volume(self):
        space = build_search_space(sample_v72(), baseline())
        self.assertEqual(space["min_volume_ratio"], [1.0, 1.25, 1.5])

    def test_search_space_stop(self):
        space = build_search_space(sample_v72(), baseline())
        self.assertEqual(space["stop_loss_pct"], [0.015, 0.02, 0.022])

    def test_search_space_target(self):
        space = build_search_space(sample_v72(), baseline())
        self.assertEqual(space["take_profit_pct"], [0.036, 0.04, 0.046])

    def test_search_space_cooldown(self):
        space = build_search_space(sample_v72(), baseline())
        self.assertEqual(space["cooldown_bars"], [2, 4, 6])

    def test_total_combinations(self):
        result = build_optimization_plan(
            sample_v72(), baseline(), max_candidates=24,
            created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["total_search_combinations"], 243)

    def test_candidate_limit(self):
        result = build_optimization_plan(
            sample_v72(), baseline(), max_candidates=10,
            created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["selected_candidate_count"], 10)

    def test_candidate_unique(self):
        result = build_optimization_plan(
            sample_v72(), baseline(), max_candidates=24,
            created_at="2026-07-30T00:00:00+00:00"
        )
        ids = [c["candidate_id"] for c in result["candidates"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_candidate_pending(self):
        result = build_optimization_plan(
            sample_v72(), baseline(), max_candidates=2,
            created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(
            result["candidates"][0]["evaluation_state"],
            "PENDING_BACKTEST",
        )

    def test_rank_sequence(self):
        result = build_optimization_plan(
            sample_v72(), baseline(), max_candidates=5,
            created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual([c["rank"] for c in result["candidates"]], [1,2,3,4,5])

    def test_candidate_id_deterministic(self):
        self.assertEqual(candidate_id(baseline()), candidate_id(baseline()))

    def test_plan_deterministic_fixed_time(self):
        a = build_optimization_plan(
            sample_v72(), baseline(), 5, "2026-07-30T00:00:00+00:00"
        )
        b = build_optimization_plan(
            sample_v72(), baseline(), 5, "2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(a, b)

    def test_hash(self):
        result = build_optimization_plan(
            sample_v72(), baseline(), 5, "2026-07-30T00:00:00+00:00"
        )
        copied = dict(result)
        observed = copied.pop("parameter_optimization_report_sha256")
        expected = hashlib.sha256(canonical_json(copied).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_live_false(self):
        result = build_optimization_plan(
            sample_v72(), baseline(), 5, "2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["approved_for_live"])

    def test_network_false(self):
        result = build_optimization_plan(
            sample_v72(), baseline(), 5, "2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["network_used"])

    def test_requires_backtest(self):
        result = build_optimization_plan(
            sample_v72(), baseline(), 5, "2026-07-30T00:00:00+00:00"
        )
        self.assertTrue(result["requires_offline_backtest"])

    def test_bad_schema(self):
        report = sample_v72()
        report["schema_version"] = "bad"
        with self.assertRaises(OptimizationError):
            build_optimization_plan(report, baseline())

    def test_bad_network(self):
        report = sample_v72()
        report["network_used"] = True
        with self.assertRaises(OptimizationError):
            build_optimization_plan(report, baseline())

    def test_bad_live(self):
        report = sample_v72()
        report["approved_for_live"] = True
        with self.assertRaises(OptimizationError):
            build_optimization_plan(report, baseline())

    def test_no_revision_required(self):
        report = sample_v72()
        report["requires_strategy_revision"] = False
        with self.assertRaises(OptimizationError):
            build_optimization_plan(report, baseline())

    def test_missing_baseline(self):
        bad = baseline()
        bad.pop("signal_threshold")
        with self.assertRaises(OptimizationError):
            build_optimization_plan(sample_v72(), bad)

    def test_invalid_threshold(self):
        bad = baseline()
        bad["signal_threshold"] = 2.0
        with self.assertRaises(OptimizationError):
            build_optimization_plan(sample_v72(), bad)

    def test_invalid_candidate_limit(self):
        with self.assertRaises(OptimizationError):
            build_optimization_plan(sample_v72(), baseline(), 0)

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            revision = root / "revision.json"
            baseline_path = root / "baseline.json"
            output = root / "out.json"
            revision.write_text(json.dumps(sample_v72()), encoding="utf-8")
            baseline_path.write_text(
                json.dumps({"parameters": baseline()}), encoding="utf-8"
            )
            code = main([
                "--revision", str(revision),
                "--baseline", str(baseline_path),
                "--output", str(output),
                "--max-candidates", "7",
            ])
            self.assertEqual(code, 0)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["selected_candidate_count"], 7)

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main([
                "--revision", str(root / "missing.json"),
                "--baseline", str(root / "baseline.json"),
                "--output", str(root / "out.json"),
            ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
