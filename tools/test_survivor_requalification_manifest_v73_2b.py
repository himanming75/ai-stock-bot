import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.survivor_requalification_manifest_v73_2b import (
    DEFAULT_MAX_SURVIVORS,
    ManifestError,
    SCHEMA_VERSION,
    VERSION,
    build_manifest,
    canonical_json,
    main,
)


def evaluation(cid, qrank, score, brank, status="PASS"):
    return {
        "candidate_id": cid,
        "quality_rank": qrank,
        "quality_score": score,
        "source_backtest_rank": brank,
        "quality_gate_status": status,
        "failure_reasons": [] if status == "PASS" else ["LOW_WIN_RATE"],
        "metrics": {
            "trade_count": 10,
            "win_rate": 0.6,
            "profit_factor": 2.0,
            "expectancy": 5.0,
            "net_pnl": 50.0,
        },
        "parameters": {
            "signal_threshold": 0.7,
            "stop_loss_pct": 0.015,
            "take_profit_pct": 0.04,
            "min_volume_ratio": 1.5,
            "cooldown_bars": 2,
        },
        "approved_for_live": False,
    }


def report():
    return {
        "status": "PASS",
        "decision": "quality_gate_survivors_available",
        "quality_gate_state": "SURVIVORS_AVAILABLE",
        "champion_strategy": "breakout",
        "revision_id": "REV-breakout-V72",
        "candidate_count": 4,
        "survivor_count": 3,
        "candidate_evaluations": [
            evaluation("CAND-B", 2, 90.0, 2),
            evaluation("CAND-A", 1, 100.0, 1),
            evaluation("CAND-C", 3, 80.0, 3),
            evaluation("CAND-D", 4, 10.0, 4, status="FAIL"),
        ],
        "requires_requalification": True,
        "approved_for_live": False,
        "network_used": False,
        "quality_gate_report_sha256": "a" * 64,
        "schema_version": "v73.2a.offline_candidate_quality_gate.1",
        "version": "73.2A",
    }


class TestV732B(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "73.2B")

    def test_schema(self):
        self.assertEqual(
            SCHEMA_VERSION,
            "v73.2b.survivor_requalification_manifest.1"
        )

    def test_default_limit(self):
        self.assertEqual(DEFAULT_MAX_SURVIVORS, 5)

    def test_manifest_pass(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["status"], "PASS")

    def test_champion(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["champion_candidate_id"], "CAND-A")

    def test_runner_up(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["runner_up_candidate_id"], "CAND-B")

    def test_fail_candidate_excluded(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertNotIn("CAND-D", result["execution_order"])

    def test_limit(self):
        result = build_manifest(
            report(),
            max_survivors=2,
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertEqual(result["selected_survivor_count"], 2)

    def test_priority_sequence(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(
            [x["requalification_priority"] for x in result["selected_candidates"]],
            [1, 2, 3],
        )

    def test_pending_state(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertTrue(
            all(
                x["requalification_state"] == "PENDING"
                for x in result["selected_candidates"]
            )
        )

    def test_required_stages(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        contract = result["validation_contracts"][0]
        self.assertEqual(
            [x["stage"] for x in contract["required_stages"]],
            ["V68", "V70", "V71"],
        )

    def test_live_false(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["approved_for_live"])

    def test_network_false(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["network_used"])

    def test_requires_execution(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertTrue(result["requires_requalification_execution"])

    def test_deterministic(self):
        a = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        b = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(a, b)

    def test_hash(self):
        result = build_manifest(
            report(), created_at="2026-07-30T00:00:00+00:00"
        )
        copied = dict(result)
        observed = copied.pop("requalification_manifest_sha256")
        expected = hashlib.sha256(canonical_json(copied).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_bad_limit(self):
        with self.assertRaises(ManifestError):
            build_manifest(report(), max_survivors=0)

    def test_bad_status(self):
        bad = report()
        bad["status"] = "FAIL"
        with self.assertRaises(ManifestError):
            build_manifest(bad)

    def test_bad_schema(self):
        bad = report()
        bad["schema_version"] = "bad"
        with self.assertRaises(ManifestError):
            build_manifest(bad)

    def test_bad_state(self):
        bad = report()
        bad["quality_gate_state"] = "NO_SURVIVORS"
        with self.assertRaises(ManifestError):
            build_manifest(bad)

    def test_bad_network(self):
        bad = report()
        bad["network_used"] = True
        with self.assertRaises(ManifestError):
            build_manifest(bad)

    def test_bad_live(self):
        bad = report()
        bad["approved_for_live"] = True
        with self.assertRaises(ManifestError):
            build_manifest(bad)

    def test_no_pass_survivors(self):
        bad = report()
        for item in bad["candidate_evaluations"]:
            item["quality_gate_status"] = "FAIL"
        with self.assertRaises(ManifestError):
            build_manifest(bad)

    def test_missing_parameters(self):
        bad = report()
        bad["candidate_evaluations"][1]["parameters"] = None
        with self.assertRaises(ManifestError):
            build_manifest(bad)

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "in.json"
            output_path = root / "out.json"
            input_path.write_text(json.dumps(report()), encoding="utf-8")
            code = main([
                "--input", str(input_path),
                "--output", str(output_path),
                "--max-survivors", "2",
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
