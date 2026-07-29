import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("broker_manager_safe_router_v33_0.py")
SPEC = importlib.util.spec_from_file_location(
    "broker_manager_safe_router_v33_0",
    MODULE_PATH,
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class BrokerManagerSafeRouterV330Tests(unittest.TestCase):
    def setUp(self):
        self.manager = MOD.BrokerManager()

    def test_health_dashboard_passes(self):
        dashboard = self.manager.health_dashboard()
        self.assertEqual(dashboard["status"], "PASS")
        self.assertTrue(dashboard["paper_trading_ready"])
        self.assertFalse(dashboard["live_transport_enabled"])

    def test_paper_route_fills(self):
        receipt = self.manager.route_order(
            broker="paper",
            mode="paper",
            symbol="AAPL",
            side="buy",
            quantity="1",
            order_type="market",
        )
        self.assertEqual(receipt.final_status, "PAPER_FILLED")
        self.assertFalse(receipt.live_transport_used)
        self.assertEqual(receipt.broker_result["status"], "filled")

    def test_invalid_order_stops_before_broker(self):
        receipt = self.manager.route_order(
            broker="paper",
            mode="paper",
            symbol="",
            side="buy",
            quantity="1",
            order_type="market",
        )
        self.assertEqual(receipt.final_status, "REJECTED_VALIDATION")
        self.assertIsNone(receipt.broker_result)

    def test_live_without_gate_is_rejected(self):
        receipt = self.manager.route_order(
            broker="ibkr",
            mode="live",
            symbol="AAPL",
            side="buy",
            quantity="1",
            order_type="market",
        )
        self.assertEqual(receipt.final_status, "REJECTED_LIVE_GATE")
        self.assertIsNone(receipt.broker_result)

    def test_approved_live_still_rejected_by_disabled_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            approval = Path(tmp) / "approval.json"
            approval.write_text(
                json.dumps({
                    "schema_version": MOD.V31.APPROVAL_SCHEMA,
                    "approved": True,
                    "confirmation_phrase": MOD.V31.LIVE_CONFIRMATION_PHRASE,
                    "paper_trading_tests_passed": True,
                    "risk_review_passed": True,
                }),
                encoding="utf-8",
            )
            receipt = self.manager.route_order(
                broker="ibkr",
                mode="live",
                symbol="AAPL",
                side="buy",
                quantity="1",
                order_type="market",
                runtime_live_flag=True,
                approval_file=approval,
            )
            self.assertEqual(receipt.final_status, "REJECTED_BROKER")
            self.assertFalse(receipt.live_transport_used)
            self.assertIn("disabled", receipt.broker_result["rejection_reason"])

    def test_certificate_is_paper_only(self):
        certificate = MOD.readiness_certificate(self.manager)
        self.assertEqual(certificate["status"], "PASS")
        self.assertEqual(
            certificate["certification_scope"],
            "PAPER_TRADING_ONLY",
        )
        self.assertFalse(certificate["live_transport_enabled"])

    def test_receipt_hash_is_present(self):
        receipt = self.manager.route_order(
            broker="paper",
            mode="paper",
            symbol="MSFT",
            side="buy",
            quantity="1",
            order_type="market",
        )
        self.assertEqual(len(receipt.receipt_sha256), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
