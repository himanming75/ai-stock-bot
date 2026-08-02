from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.next_order_preview import (
    ControlledNextOrderExecutionPreview,
    NextOrderPreviewState,
)


def cycle_result(state="WAIT_ACTIVE_ORDER", **overrides):
    value = {
        "state": state,
        "preview_ready": state == "READY_FOR_SINGLE_ORDER_PREVIEW",
        "next_order_allowed": state == "READY_FOR_SINGLE_ORDER_PREVIEW",
        "safe_mode_engaged": False,
    }
    value.update(overrides)
    return value


def token(**overrides):
    value = {
        "cycle_id": "NEXT-abc",
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": "1",
        "estimated_price": "50",
        "estimated_notional": "50",
    }
    value.update(overrides)
    return value


class PreviewTests(unittest.TestCase):
    def build(self, cycle, tok=None, account=None, risk=None, exposure=None):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            builder=ControlledNextOrderExecutionPreview(
                preview_path=base/"preview.json",
                risk_snapshot_path=base/"risk.json",
                exposure_snapshot_path=base/"exposure.json",
                approval_gate_path=base/"approval.json",
            )
            report=builder.build(
                cycle_result=cycle,
                cycle_token=tok,
                account_snapshot=account or {
                    "status":"ACTIVE",
                    "trading_blocked":False,
                },
                risk_snapshot=risk or {"approved":True},
                exposure_snapshot=exposure or {"approved":True},
                created_at="2026-08-02T13:00:00+00:00",
                max_quantity="1",
                max_notional="100",
            )
            exists={
                "preview":(base/"preview.json").exists(),
                "risk":(base/"risk.json").exists(),
                "exposure":(base/"exposure.json").exists(),
                "approval":(base/"approval.json").exists(),
            }
        return report,exists

    def test_wait_cycle_token(self):
        r,e=self.build(cycle_result())
        self.assertEqual(r.state,NextOrderPreviewState.WAIT_CYCLE_TOKEN)
        self.assertFalse(any(e.values()))

    def test_upstream_safe_mode(self):
        r,_=self.build(cycle_result("SAFE_MODE",safe_mode_engaged=True))
        self.assertTrue(r.safe_mode_engaged)

    def test_missing_token_safe_mode(self):
        r,_=self.build(cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"))
        self.assertEqual(r.state,NextOrderPreviewState.SAFE_MODE)

    def test_ready_creates_package(self):
        r,e=self.build(
            cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
            token(),
        )
        self.assertEqual(
            r.state,
            NextOrderPreviewState.READY_FOR_SUBMISSION_APPROVAL,
        )
        self.assertTrue(r.preview_created)
        self.assertTrue(all(e.values()))
        self.assertFalse(r.actual_submission_allowed)

    def test_invalid_side(self):
        r,_=self.build(
            cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
            token(side="SHORT"),
        )
        self.assertTrue(r.safe_mode_engaged)

    def test_quantity_cap(self):
        r,_=self.build(
            cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
            token(quantity="2",estimated_notional="100"),
        )
        self.assertTrue(r.safe_mode_engaged)

    def test_notional_cap(self):
        r,_=self.build(
            cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
            token(estimated_notional="150"),
        )
        self.assertTrue(r.safe_mode_engaged)

    def test_account_inactive(self):
        r,_=self.build(
            cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
            token(),
            account={"status":"INACTIVE","trading_blocked":False},
        )
        self.assertTrue(r.safe_mode_engaged)

    def test_trading_blocked(self):
        r,_=self.build(
            cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
            token(),
            account={"status":"ACTIVE","trading_blocked":True},
        )
        self.assertTrue(r.safe_mode_engaged)

    def test_risk_not_approved(self):
        r,_=self.build(
            cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
            token(),
            risk={"approved":False},
        )
        self.assertFalse(r.risk_ok)
        self.assertTrue(r.safe_mode_engaged)

    def test_exposure_not_approved(self):
        r,_=self.build(
            cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
            token(),
            exposure={"approved":False},
        )
        self.assertFalse(r.exposure_ok)

    def test_duplicate_preview(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            builder=ControlledNextOrderExecutionPreview(
                preview_path=base/"preview.json",
                risk_snapshot_path=base/"risk.json",
                exposure_snapshot_path=base/"exposure.json",
                approval_gate_path=base/"approval.json",
            )
            kwargs=dict(
                cycle_result=cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
                cycle_token=token(),
                account_snapshot={"status":"ACTIVE","trading_blocked":False},
                risk_snapshot={"approved":True},
                exposure_snapshot={"approved":True},
                created_at="now",
            )
            one=builder.build(**kwargs)
            two=builder.build(**kwargs)
            self.assertTrue(one.preview_created)
            self.assertEqual(two.state,NextOrderPreviewState.DUPLICATE_PREVIEW)

    def test_market_order_day_tif(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            builder=ControlledNextOrderExecutionPreview(
                preview_path=base/"preview.json",
                risk_snapshot_path=base/"risk.json",
                exposure_snapshot_path=base/"exposure.json",
                approval_gate_path=base/"approval.json",
            )
            builder.build(
                cycle_result=cycle_result("READY_FOR_SINGLE_ORDER_PREVIEW"),
                cycle_token=token(),
                account_snapshot={"status":"ACTIVE","trading_blocked":False},
                risk_snapshot={"approved":True},
                exposure_snapshot={"approved":True},
                created_at="now",
            )
            raw=__import__("json").loads((base/"preview.json").read_text())
            self.assertEqual(raw["broker_payload"]["type"],"market")
            self.assertEqual(raw["broker_payload"]["time_in_force"],"day")

    def test_zero_writes(self):
        r,_=self.build(cycle_result())
        self.assertEqual(r.write_requests_executed,0)
        self.assertEqual(r.actual_paper_orders_submitted,0)
        self.assertEqual(r.live_orders_submitted,0)

    def test_json(self):
        r,_=self.build(cycle_result())
        self.assertEqual(r.to_json_dict()["state"],"WAIT_CYCLE_TOKEN")


if __name__=="__main__":
    unittest.main()
