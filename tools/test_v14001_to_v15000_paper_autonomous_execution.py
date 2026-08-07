from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_autonomous_execution.config import PaperExecutionProfile
from paper_autonomous_execution.service import PaperAutonomousExecutionService
from paper_autonomous_execution.signals import select_candidate


class Tests(unittest.TestCase):
    def test_profile_rejects_live(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "profile.json"
            p.write_text(json.dumps({
                "profile_name": "x",
                "paper_submission_enabled": True,
                "live_submission_enabled": True,
                "max_orders_per_session": 1,
                "max_notional_per_order": 25,
                "allowed_symbols": ["AAPL"],
                "min_confidence": 0.7,
                "min_reward_risk": 1.0,
                "poll_seconds": 30,
                "require_market_open": True,
                "require_manual_arm_token": True
            }), encoding="utf-8")
            self.assertIn(
                "LIVE_SUBMISSION_MUST_REMAIN_OFF",
                PaperExecutionProfile.load(p).validate(),
            )

    def test_candidate_selection(self):
        selected = select_candidate(
            [{
                "symbol": "AAPL",
                "action": "BUY",
                "reward_risk": 1.5,
                "execution_mode": "ANALYSIS_ONLY",
                "confidence_calibration": {
                    "calibrated_confidence": 0.8
                },
            }],
            allowed_symbols=("AAPL",),
            min_confidence=0.7,
            min_reward_risk=1.0,
        )
        self.assertEqual(selected["symbol"], "AAPL")

    def test_no_signal(self):
        self.assertIsNone(select_candidate(
            [],
            allowed_symbols=("AAPL",),
            min_confidence=0.7,
            min_reward_risk=1.0,
        ))

    def test_dry_run_never_submits(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            profile = root / "profile.json"
            profile.write_text(json.dumps({
                "profile_name": "test",
                "paper_submission_enabled": True,
                "live_submission_enabled": False,
                "max_orders_per_session": 1,
                "max_notional_per_order": 25,
                "allowed_symbols": ["AAPL"],
                "min_confidence": 0.7,
                "min_reward_risk": 1.0,
                "poll_seconds": 30,
                "require_market_open": False,
                "require_manual_arm_token": False
            }), encoding="utf-8")
            signal = root / "release/v11001_12000_multi_timeframe_ai/actual"
            signal.mkdir(parents=True)
            (signal / "multi_timeframe_ai_report_bilingual.json").write_text(
                json.dumps({"analyses": [{
                    "symbol": "AAPL",
                    "action": "BUY",
                    "reward_risk": 2.0,
                    "execution_mode": "ANALYSIS_ONLY",
                    "confidence_calibration": {
                        "calibrated_confidence": 0.9
                    },
                }]}),
                encoding="utf-8",
            )
            service = PaperAutonomousExecutionService(
                project_root=root,
                profile_path=profile,
                output_dir=root / "out",
            )
            with patch.object(
                service,
                "preflight",
                return_value={"status": "PASS"},
            ), patch.object(
                service.adapter,
                "submit_market_notional",
            ) as submit:
                result = service.run_once(allow_submit=False)
                submit.assert_not_called()
                self.assertEqual(result["status"], "READY_DRY_RUN")
                self.assertFalse(result["paper_order_submitted"])

    def test_certification_zero_orders(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            profile = root / "profile.json"
            profile.write_text(json.dumps({
                "profile_name": "test",
                "paper_submission_enabled": True,
                "live_submission_enabled": False,
                "max_orders_per_session": 1,
                "max_notional_per_order": 25,
                "allowed_symbols": ["AAPL"],
                "min_confidence": 0.7,
                "min_reward_risk": 1.0,
                "poll_seconds": 30,
                "require_market_open": False,
                "require_manual_arm_token": False
            }), encoding="utf-8")
            service = PaperAutonomousExecutionService(
                project_root=root,
                profile_path=profile,
                output_dir=root / "out",
            )
            with patch.object(
                service,
                "preflight",
                return_value={"status": "PASS"},
            ):
                result = service.certify()
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["actual_paper_orders_submitted_during_build"], 0
            )
            self.assertFalse(result["live_submission_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
