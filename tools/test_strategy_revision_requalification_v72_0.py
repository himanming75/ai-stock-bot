import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.strategy_revision_requalification_v72_0 import (
    SCHEMA_VERSION,
    VERSION,
    RevisionAnalysisError,
    analyze_window,
    build_revision_report,
    canonical_json,
    main,
)


def sample_report(rejected=True):
    windows = [
        {
            "window": 1,
            "window_status": "FAIL",
            "expectancy_retention": "-0.057681",
            "train_metrics": {"expectancy": "11.7093"},
            "forward_metrics": {
                "expectancy": "-0.6754",
                "win_rate": "0.250000",
                "profit_factor": "0.926246",
            },
        },
        {
            "window": 2,
            "window_status": "FAIL",
            "expectancy_retention": "0.517581",
            "train_metrics": {"expectancy": "9.7689"},
            "forward_metrics": {
                "expectancy": "5.0562",
                "win_rate": "0.400000",
                "profit_factor": "1.695707",
            },
        },
        {
            "window": 3,
            "window_status": "PASS",
            "expectancy_retention": "0.997858",
            "train_metrics": {"expectancy": "4.8090"},
            "forward_metrics": {
                "expectancy": "4.7987",
                "win_rate": "0.450000",
                "profit_factor": "1.631495",
            },
        },
        {
            "window": 4,
            "window_status": "FAIL",
            "expectancy_retention": "-0.301643",
            "train_metrics": {"expectancy": "5.0888"},
            "forward_metrics": {
                "expectancy": "-1.5350",
                "win_rate": "0.300000",
                "profit_factor": "0.843601",
            },
        },
    ]

    if not rejected:
        windows = [{
            "window": 1,
            "window_status": "PASS",
            "expectancy_retention": "0.800000",
            "train_metrics": {"expectancy": "5.0000"},
            "forward_metrics": {
                "expectancy": "4.0000",
                "win_rate": "0.600000",
                "profit_factor": "1.500000",
            },
        }]

    return {
        "status": "PASS",
        "decision": (
            "walk_forward_validation_rejected"
            if rejected else "walk_forward_validation_approved"
        ),
        "validation_state": "REJECTED" if rejected else "APPROVED",
        "champion_strategy": "breakout",
        "window_count": len(windows),
        "pass_count": sum(1 for w in windows if w["window_status"] == "PASS"),
        "fail_count": sum(1 for w in windows if w["window_status"] == "FAIL"),
        "pass_rate": "0.250000" if rejected else "1.000000",
        "requires_monte_carlo_validation": not rejected,
        "windows": windows,
        "approved_for_live": False,
        "network_used": False,
        "walk_forward_report_sha256": "a" * 64,
        "schema_version": "v70.0.walk_forward_validation.1",
        "version": "70.0",
    }


class TestV72(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "72.0")

    def test_schema(self):
        self.assertEqual(
            SCHEMA_VERSION,
            "v72.0.strategy_revision_requalification.1",
        )

    def test_window_one_reasons(self):
        result = analyze_window(sample_report()["windows"][0])
        self.assertIn("LOW_WIN_RATE", result["failure_reasons"])
        self.assertIn("LOW_PROFIT_FACTOR", result["failure_reasons"])
        self.assertIn("NON_POSITIVE_EXPECTANCY", result["failure_reasons"])
        self.assertIn("LOW_EXPECTANCY_RETENTION", result["failure_reasons"])

    def test_window_two_only_win_rate(self):
        result = analyze_window(sample_report()["windows"][1])
        self.assertEqual(result["failure_reasons"], ["LOW_WIN_RATE"])

    def test_pass_window(self):
        result = analyze_window(sample_report()["windows"][2])
        self.assertEqual(result["failure_reasons"], [])
        self.assertEqual(result["severity"], "NONE")

    def test_rejected_requires_revision(self):
        result = build_revision_report(
            sample_report(),
            revision_id="REV-TEST",
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertTrue(result["requires_strategy_revision"])

    def test_rejected_counts(self):
        result = build_revision_report(
            sample_report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["pass_window_count"], 1)
        self.assertEqual(result["fail_window_count"], 3)

    def test_failure_distribution(self):
        result = build_revision_report(
            sample_report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(
            result["failure_distribution"]["LOW_WIN_RATE"]["count"], 3
        )

    def test_expectancy_count(self):
        result = build_revision_report(
            sample_report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(
            result["failure_distribution"]["NON_POSITIVE_EXPECTANCY"]["count"],
            2,
        )

    def test_recommendations_created(self):
        result = build_revision_report(
            sample_report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertGreaterEqual(len(result["recommendations"]), 4)

    def test_requalification_pipeline(self):
        result = build_revision_report(
            sample_report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertIn(
            "v70_walk_forward_validation",
            result["revision_plan"]["pipeline"],
        )

    def test_no_revision_needed(self):
        result = build_revision_report(
            sample_report(False), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["requires_strategy_revision"])
        self.assertEqual(
            result["requalification_state"], "NO_REVISION_REQUIRED"
        )

    def test_live_false(self):
        result = build_revision_report(
            sample_report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["approved_for_live"])

    def test_network_false(self):
        result = build_revision_report(
            sample_report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertFalse(result["network_used"])

    def test_deterministic_with_fixed_time(self):
        a = build_revision_report(
            sample_report(),
            revision_id="REV-X",
            created_at="2026-07-30T00:00:00+00:00",
        )
        b = build_revision_report(
            sample_report(),
            revision_id="REV-X",
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertEqual(a, b)

    def test_hash(self):
        result = build_revision_report(
            sample_report(),
            revision_id="REV-X",
            created_at="2026-07-30T00:00:00+00:00",
        )
        copied = dict(result)
        observed = copied.pop("strategy_revision_report_sha256")
        expected = hashlib.sha256(canonical_json(copied).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_bad_schema(self):
        report = sample_report()
        report["schema_version"] = "bad"
        with self.assertRaises(RevisionAnalysisError):
            build_revision_report(report)

    def test_bad_status(self):
        report = sample_report()
        report["status"] = "FAIL"
        with self.assertRaises(RevisionAnalysisError):
            build_revision_report(report)

    def test_bad_network(self):
        report = sample_report()
        report["network_used"] = True
        with self.assertRaises(RevisionAnalysisError):
            build_revision_report(report)

    def test_bad_live(self):
        report = sample_report()
        report["approved_for_live"] = True
        with self.assertRaises(RevisionAnalysisError):
            build_revision_report(report)

    def test_bad_window_count(self):
        report = sample_report()
        report["window_count"] = 99
        with self.assertRaises(RevisionAnalysisError):
            build_revision_report(report)

    def test_status_mismatch(self):
        window = sample_report()["windows"][0]
        window["window_status"] = "PASS"
        with self.assertRaises(RevisionAnalysisError):
            analyze_window(window)

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "in.json"
            out = root / "out.json"
            inp.write_text(json.dumps(sample_report()), encoding="utf-8")
            code = main([
                "--input", str(inp),
                "--revision-id", "REV-CLI",
                "--output", str(out),
            ])
            self.assertEqual(code, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["revision_id"], "REV-CLI")

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main([
                "--input", str(root / "missing.json"),
                "--output", str(root / "out.json"),
            ])
            self.assertEqual(code, 1)

    def test_revision_id_default(self):
        result = build_revision_report(
            sample_report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["revision_id"], "REV-breakout-V72")

    def test_critical_severity_exists(self):
        result = build_revision_report(
            sample_report(), created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(result["severity_distribution"]["CRITICAL"], 2)


if __name__ == "__main__":
    unittest.main()
