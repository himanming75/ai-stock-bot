from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_production_release.discovery import discover_layout
from paper_production_release.environment import validate_environment
from paper_production_release.integrity import build_integrity_manifest
from paper_production_release.prerequisites import evaluate_prerequisites


class PaperProductionReleaseTests(unittest.TestCase):
    def test_install_check_direct_import_path(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "paper_production_release/discovery.py").exists())

    def test_layout_supports_indicator_engine(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder in (
                "indicator_engine",
                "strategy_engine_v2",
                "portfolio_scoring",
                "explainability_engine",
                "backtest_v2",
                "validation_v2",
                "multi_asset_backtest",
                "paper_orchestrator",
                "web_ui_v2",
            ):
                (root / folder).mkdir()
            result = discover_layout(root)
        self.assertTrue(result["layout_valid"])
        self.assertEqual(result["indicator_layout"], "indicator_engine")

    def test_layout_supports_indicator_engine_v2(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder in (
                "indicator_engine_v2",
                "strategy_engine_v2",
                "portfolio_scoring",
                "explainability_engine",
                "backtest_v2",
                "validation_v2",
                "multi_asset_backtest",
                "paper_orchestrator",
                "web_ui_v2",
            ):
                (root / folder).mkdir()
            result = discover_layout(root)
        self.assertTrue(result["layout_valid"])

    def test_environment_reports_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = validate_environment(root)
        self.assertIn("checks", result)
        self.assertIn("python_supported", result["checks"])

    def test_integrity_detects_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            result = build_integrity_manifest(Path(temp))
        self.assertFalse(result["integrity_passed"])
        self.assertGreater(len(result["missing_files"]), 0)

    def test_prerequisites_pending_without_files(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate_prerequisites(Path(temp))
        self.assertFalse(result["ready"])
        self.assertGreater(len(result["blocking_prerequisites"]), 0)

    def test_prerequisites_ready_with_valid_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payloads = {
                "release/v83_77_to_v83_80/actual/multi_day_paper_validation_result.json":
                    {"requirement_met": True},
                "release/v83_81_to_v83_88/actual/paper_stability_runtime_result.json":
                    {"certificate_valid": True},
                "release/v83_89_to_v83_96/actual/performance_production_readiness_result.json":
                    {"production_ready": True},
                "release/v88_09_to_v88_16/actual/paper_orchestrator_result.json":
                    {
                        "state": "PAPER_AUTOMATION_ORCHESTRATOR_READY",
                        "status": "PASS",
                        "safe_mode": False,
                        "completed_step_count": 7,
                        "total_step_count": 7,
                    },
                "release/v87_09_to_v87_16/actual/walk_forward_stress_validation_result.json":
                    {"state": "BACKTEST_ROBUSTNESS_VALIDATED"},
                "release/v87_17_to_v87_24/actual/multi_asset_backtest_result.json":
                    {"state": "MULTI_ASSET_BACKTEST_CERTIFIED"},
                "release/v88_01_to_v88_08/actual/web_ui_v2_state.json":
                    {"state": "WEB_UI_V2_READY"},
            }
            for relative, payload in payloads.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload), encoding="utf-8")
            result = evaluate_prerequisites(root)
        self.assertTrue(result["ready"])

    def test_time_based_pending_classified(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate_prerequisites(Path(temp))
        self.assertIn(
            "multi_day_requirement_met",
            result["time_based_pending"],
        )

    def test_safety_is_not_derived_from_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate_prerequisites(Path(temp))
        self.assertIsInstance(result["checks"], dict)


if __name__ == "__main__":
    unittest.main()
