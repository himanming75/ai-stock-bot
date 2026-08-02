from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.final_submission_approval import (
    FinalPaperSubmissionApprovalGate,
    FinalSubmissionApprovalState,
)


def preview_result(state="WAIT_CYCLE_TOKEN", **overrides):
    value = {
        "state": state,
        "preview_created": state == "READY_FOR_SUBMISSION_APPROVAL",
        "payload_valid": state == "READY_FOR_SUBMISSION_APPROVAL",
        "risk_ok": state == "READY_FOR_SUBMISSION_APPROVAL",
        "exposure_ok": state == "READY_FOR_SUBMISSION_APPROVAL",
        "safe_mode_engaged": False,
        "preview_id": "PREVIEW-abc",
    }
    value.update(overrides)
    return value


def preview():
    return {
        "preview_id": "PREVIEW-abc",
        "cycle_id": "NEXT-abc",
        "client_order_id": "BOT-AUTO-PAPER-V137-abc",
    }


class ApprovalTests(unittest.TestCase):
    def evaluate(
        self,
        *,
        result=None,
        phrase="",
        order=None,
        risk=None,
        exposure=None,
        gate=None,
    ):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            approval=FinalPaperSubmissionApprovalGate(
                approval_token_path=base/"approval.json",
                approval_audit_path=base/"audit.json",
            )
            report=approval.evaluate(
                preview_result=result or preview_result(),
                order_preview=order,
                risk_snapshot=risk,
                exposure_snapshot=exposure,
                approval_gate=gate,
                approval_phrase=phrase,
                approved_at="2026-08-02T14:00:00+00:00",
            )
            exists={
                "token":(base/"approval.json").exists(),
                "audit":(base/"audit.json").exists(),
            }
        return report,exists

    def ready_kwargs(self):
        return dict(
            result=preview_result("READY_FOR_SUBMISSION_APPROVAL"),
            order=preview(),
            risk={"approved":True},
            exposure={"approved":True},
            gate={"actual_submission_allowed":False},
        )

    def test_wait_preview_package(self):
        r,e=self.evaluate()
        self.assertEqual(r.state,FinalSubmissionApprovalState.WAIT_PREVIEW_PACKAGE)
        self.assertFalse(any(e.values()))

    def test_upstream_safe_mode(self):
        r,_=self.evaluate(
            result=preview_result("SAFE_MODE",safe_mode_engaged=True)
        )
        self.assertTrue(r.safe_mode_engaged)

    def test_missing_order_preview(self):
        kwargs=self.ready_kwargs();kwargs["order"]=None
        r,_=self.evaluate(**kwargs)
        self.assertEqual(r.state,FinalSubmissionApprovalState.SAFE_MODE)

    def test_risk_not_approved(self):
        kwargs=self.ready_kwargs();kwargs["risk"]={"approved":False}
        r,_=self.evaluate(**kwargs)
        self.assertTrue(r.safe_mode_engaged)

    def test_exposure_not_approved(self):
        kwargs=self.ready_kwargs();kwargs["exposure"]={"approved":False}
        r,_=self.evaluate(**kwargs)
        self.assertTrue(r.safe_mode_engaged)

    def test_missing_gate(self):
        kwargs=self.ready_kwargs();kwargs["gate"]=None
        r,_=self.evaluate(**kwargs)
        self.assertTrue(r.safe_mode_engaged)

    def test_preview_gate_must_block_submission(self):
        kwargs=self.ready_kwargs();kwargs["gate"]={"actual_submission_allowed":True}
        r,_=self.evaluate(**kwargs)
        self.assertTrue(r.safe_mode_engaged)

    def test_wrong_phrase_waits(self):
        r,_=self.evaluate(
            **self.ready_kwargs(),
            phrase="APPROVE",
        )
        self.assertEqual(
            r.state,
            FinalSubmissionApprovalState.READY_FOR_HUMAN_APPROVAL,
        )
        self.assertFalse(r.actual_submission_allowed)

    def test_exact_phrase_approves(self):
        r,e=self.evaluate(
            **self.ready_kwargs(),
            phrase=FinalPaperSubmissionApprovalGate.REQUIRED_PHRASE,
        )
        self.assertEqual(
            r.state,
            FinalSubmissionApprovalState.APPROVED_FOR_SINGLE_PAPER_SUBMISSION,
        )
        self.assertTrue(r.human_approval_verified)
        self.assertTrue(r.actual_submission_allowed)
        self.assertTrue(all(e.values()))

    def test_duplicate_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            approval=FinalPaperSubmissionApprovalGate(
                approval_token_path=base/"approval.json",
                approval_audit_path=base/"audit.json",
            )
            kwargs=dict(
                preview_result=preview_result("READY_FOR_SUBMISSION_APPROVAL"),
                order_preview=preview(),
                risk_snapshot={"approved":True},
                exposure_snapshot={"approved":True},
                approval_gate={"actual_submission_allowed":False},
                approval_phrase=FinalPaperSubmissionApprovalGate.REQUIRED_PHRASE,
                approved_at="now",
            )
            one=approval.evaluate(**kwargs)
            two=approval.evaluate(**kwargs)
            self.assertTrue(one.approval_token_created)
            self.assertEqual(
                two.state,
                FinalSubmissionApprovalState.DUPLICATE_APPROVAL,
            )
            self.assertTrue(two.duplicate_approval)

    def test_no_broker_write(self):
        r,_=self.evaluate()
        self.assertEqual(r.write_requests_executed,0)
        self.assertEqual(r.actual_paper_orders_submitted,0)
        self.assertEqual(r.live_orders_submitted,0)

    def test_json(self):
        r,_=self.evaluate()
        self.assertEqual(
            r.to_json_dict()["state"],
            "WAIT_PREVIEW_PACKAGE",
        )


if __name__=="__main__":
    unittest.main()
