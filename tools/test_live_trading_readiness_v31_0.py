import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("live_trading_readiness_v31_0.py")
SPEC = importlib.util.spec_from_file_location("live_trading_readiness_v31_0", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class LiveTradingReadinessV310Tests(unittest.TestCase):
    def order(self, **overrides):
        data = {
            "symbol": "AAPL",
            "side": MOD.OrderSide.BUY,
            "quantity": "2",
            "order_type": MOD.OrderType.MARKET,
            "time_in_force": MOD.TimeInForce.DAY,
            "limit_price": None,
            "client_order_id": "test-order-001",
        }
        data.update(overrides)
        return MOD.OrderRequest(**data)

    def test_valid_paper_order_is_dry_run(self):
        receipt = MOD.execute_order(
            self.order(),
            mode=MOD.TradingMode.PAPER,
        )
        self.assertEqual(receipt.status, "DRY_RUN_ACCEPTED")
        self.assertTrue(receipt.dry_run)
        self.assertFalse(receipt.live_transport_implemented)

    def test_invalid_limit_order_rejected(self):
        receipt = MOD.execute_order(
            self.order(order_type=MOD.OrderType.LIMIT, limit_price=None),
            mode=MOD.TradingMode.PAPER,
        )
        self.assertEqual(receipt.status, "REJECTED_VALIDATION")
        self.assertTrue(receipt.validation_errors)

    def test_live_mode_requires_double_lock(self):
        receipt = MOD.execute_order(
            self.order(),
            mode=MOD.TradingMode.LIVE,
            runtime_live_flag=False,
            approval_file=None,
        )
        self.assertEqual(receipt.status, "REJECTED_LIVE_GATE")
        self.assertGreaterEqual(len(receipt.gate_reasons), 2)

    def test_approved_live_mode_still_has_no_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            approval = Path(tmp) / "approval.json"
            approval.write_text(
                json.dumps({
                    "schema_version": MOD.APPROVAL_SCHEMA,
                    "approved": True,
                    "confirmation_phrase": MOD.LIVE_CONFIRMATION_PHRASE,
                    "paper_trading_tests_passed": True,
                    "risk_review_passed": True,
                }),
                encoding="utf-8",
            )
            receipt = MOD.execute_order(
                self.order(),
                mode=MOD.TradingMode.LIVE,
                runtime_live_flag=True,
                approval_file=approval,
            )
            self.assertEqual(
                receipt.status,
                "SIMULATED_LIVE_READY_NO_TRANSPORT",
            )
            self.assertTrue(receipt.dry_run)
            self.assertFalse(receipt.live_transport_implemented)

    def test_approval_template_is_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "template.json"
            MOD.create_approval_template(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(payload["approved"])
            self.assertFalse(payload["paper_trading_tests_passed"])
            self.assertEqual(payload["confirmation_phrase"], "")

    def test_receipt_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            receipt = MOD.execute_order(
                self.order(),
                mode=MOD.TradingMode.PAPER,
            )
            MOD.write_receipt(path, receipt)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "DRY_RUN_ACCEPTED")
            self.assertEqual(payload["mode"], "paper")


if __name__ == "__main__":
    unittest.main(verbosity=2)
