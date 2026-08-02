from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path

from autonomous_paper_runtime.autonomous_paper_order_launch import (
    APPROVAL_PHRASE,
    AutonomousPaperOrderLaunch,
)


class Tests(unittest.TestCase):
    def eligibility_result(self):
        return {
            "status": "PASS",
            "state": "NEXT_ORDER_ELIGIBLE",
            "cycle_id": "cycle-001",
            "eligibility_id": "eligibility-001",
            "eligible": True,
            "safe_mode_engaged": False,
        }

    def eligibility_token(self):
        return {
            "cycle_id": "cycle-001",
            "eligibility_id": "eligibility-001",
            "eligible": True,
        }

    def candidate(self):
        return {
            "symbol": "SPY",
            "side": "BUY",
            "quantity": 1,
            "order_type": "MARKET",
            "time_in_force": "DAY",
            "signal_id": "signal-001",
            "strategy": "test_strategy",
            "risk_approved": True,
        }

    def run_case(self, result, token=None, candidate=None, approval="", enabled=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        result_path = root / "eligibility_result.json"
        token_path = root / "eligibility_token.json"
        candidate_path = root / "candidate.json"
        preview_path = root / "preview.json"
        prep_path = root / "prep.json"
        output_path = root / "result.json"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        if token is not None:
            token_path.write_text(json.dumps(token), encoding="utf-8")
        if candidate is not None:
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
        report = AutonomousPaperOrderLaunch().run(
            eligibility_result_path=result_path,
            eligibility_token_path=token_path,
            order_candidate_path=candidate_path,
            preview_path=preview_path,
            preparation_token_path=prep_path,
            result_path=output_path,
            approval_phrase=approval,
            enable_submission=enabled,
        )
        return report, preview_path, prep_path

    def test_waits_before_eligibility(self):
        report, preview, prep = self.run_case({
            "status": "PASS",
            "state": "WAIT_CYCLE_RESUME",
            "cycle_id": "",
            "eligibility_id": "",
            "eligible": False,
            "safe_mode_engaged": False,
        })
        self.assertEqual(report.state, "WAIT_ELIGIBILITY")
        self.assertFalse(preview.exists())
        self.assertFalse(prep.exists())

    def test_valid_inputs_create_preview_and_wait_approval(self):
        report, preview, prep = self.run_case(
            self.eligibility_result(),
            self.eligibility_token(),
            self.candidate(),
        )
        self.assertEqual(report.state, "WAIT_APPROVAL")
        self.assertTrue(report.preview_ready)
        self.assertTrue(preview.exists())
        self.assertFalse(prep.exists())

    def test_approval_without_enable_is_disabled(self):
        report, _, prep = self.run_case(
            self.eligibility_result(),
            self.eligibility_token(),
            self.candidate(),
            approval=APPROVAL_PHRASE,
            enabled=False,
        )
        self.assertEqual(report.state, "SUBMISSION_DISABLED")
        self.assertFalse(report.submission_prepared)
        self.assertFalse(prep.exists())

    def test_approval_and_enable_prepare_local_token_only(self):
        report, _, prep = self.run_case(
            self.eligibility_result(),
            self.eligibility_token(),
            self.candidate(),
            approval=APPROVAL_PHRASE,
            enabled=True,
        )
        self.assertEqual(report.state, "ORDER_SUBMISSION_PREPARED")
        self.assertTrue(report.submission_prepared)
        self.assertTrue(prep.exists())
        self.assertEqual(report.network_requests_executed, 0)
        self.assertEqual(report.actual_paper_orders_submitted, 0)

    def test_token_mismatch_blocks(self):
        token = self.eligibility_token()
        token["cycle_id"] = "cycle-other"
        report, _, _ = self.run_case(
            self.eligibility_result(), token, self.candidate()
        )
        self.assertEqual(report.status, "BLOCKED")

    def test_invalid_candidate_blocks(self):
        candidate = self.candidate()
        candidate["quantity"] = 0
        report, _, _ = self.run_case(
            self.eligibility_result(), self.eligibility_token(), candidate
        )
        self.assertEqual(report.status, "BLOCKED")

    def test_limit_requires_positive_price(self):
        candidate = self.candidate()
        candidate["order_type"] = "LIMIT"
        candidate["limit_price"] = 0
        report, _, _ = self.run_case(
            self.eligibility_result(), self.eligibility_token(), candidate
        )
        self.assertEqual(report.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
