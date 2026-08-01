from pathlib import Path
from tempfile import TemporaryDirectory
import json, unittest
from alpaca_market_data.paper_trading_readiness_v80_01_05 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.config = PaperReadinessConfig()

    def test_config(self):
        self.config.validate()

    def test_network_rejected(self):
        with self.assertRaises(ValueError):
            PaperReadinessConfig(network_probe_enabled=True).validate()

    def test_credentials_rejected(self):
        with self.assertRaises(ValueError):
            PaperReadinessConfig(credentials_required=True).validate()

    def test_policy(self):
        policy = build_paper_policy(self.config)
        self.assertFalse(policy["capabilities"]["order_submit"])
        self.assertFalse(policy["capabilities"]["broker_network_connect"])

    def test_probe(self):
        probe = build_capability_probe(build_paper_policy(self.config))
        self.assertEqual(probe["status"], "PASS")
        self.assertEqual(probe["forbidden_capability_count"], 0)

    def test_intent(self):
        intent = build_order_intent("aapl", "buy", 2, 100)
        self.assertEqual(intent["symbol"], "AAPL")
        self.assertFalse(intent["broker_submission_authorized"])

    def test_bad_intent_quantity(self):
        with self.assertRaises(ValueError):
            build_order_intent("AAPL", "BUY", 0, 100)

    def test_adapter_receipt(self):
        policy = build_paper_policy(self.config)
        adapter = NoNetworkPaperAdapter(policy)
        receipt = adapter.validate_intent(
            build_order_intent("AAPL", "BUY", 1, 100)
        )
        self.assertEqual(receipt["status"], "ACCEPTED_DRY_RUN")
        self.assertIsNone(receipt["broker_order_id"])
        self.assertEqual(receipt["actual_orders_submitted"], 0)

    def test_intent_tamper(self):
        policy = build_paper_policy(self.config)
        adapter = NoNetworkPaperAdapter(policy)
        intent = build_order_intent("AAPL", "BUY", 1, 100)
        intent["quantity"] = 2
        with self.assertRaises(ValueError):
            adapter.validate_intent(intent)

    def test_assessment(self):
        historical = {
            "completion_summary": {"historical_engine_complete": True}
        }
        policy = build_paper_policy(self.config)
        probe = build_capability_probe(policy)
        adapter = NoNetworkPaperAdapter(policy)
        receipts = [
            adapter.validate_intent(
                build_order_intent("AAPL", "BUY", 1, 100)
            )
        ]
        assessment = build_readiness_assessment(
            historical, policy, probe, receipts
        )
        self.assertEqual(assessment["status"], "PASS")
        self.assertFalse(assessment["paper_trading_authorized"])

    def test_store_reuse(self):
        with TemporaryDirectory() as temp:
            output = Path(temp)
            policy = build_paper_policy(self.config)
            probe = build_capability_probe(policy)
            adapter = NoNetworkPaperAdapter(policy)
            receipts = [
                adapter.validate_intent(
                    build_order_intent("AAPL", "BUY", 1, 100)
                )
            ]
            assessment = build_readiness_assessment(
                {"completion_summary": {"historical_engine_complete": True}},
                policy, probe, receipts
            )
            store_readiness_package(
                output, policy, probe, receipts, assessment
            )
            second = store_readiness_package(
                output, policy, probe, receipts, assessment
            )
            self.assertTrue(second["reused_existing_package"])

    def test_manifest(self):
        with TemporaryDirectory() as temp:
            output = Path(temp)
            policy = build_paper_policy(self.config)
            probe = build_capability_probe(policy)
            adapter = NoNetworkPaperAdapter(policy)
            receipts = [
                adapter.validate_intent(
                    build_order_intent("AAPL", "BUY", 1, 100)
                )
            ]
            assessment = build_readiness_assessment(
                {"completion_summary": {"historical_engine_complete": True}},
                policy, probe, receipts
            )
            stored = store_readiness_package(
                output, policy, probe, receipts, assessment
            )
            self.assertTrue(
                verify_readiness_manifest(output, stored["manifest"])
            )

    def test_manifest_tamper(self):
        with TemporaryDirectory() as temp:
            output = Path(temp)
            policy = build_paper_policy(self.config)
            probe = build_capability_probe(policy)
            adapter = NoNetworkPaperAdapter(policy)
            receipts = [
                adapter.validate_intent(
                    build_order_intent("AAPL", "BUY", 1, 100)
                )
            ]
            assessment = build_readiness_assessment(
                {"completion_summary": {"historical_engine_complete": True}},
                policy, probe, receipts
            )
            stored = store_readiness_package(
                output, policy, probe, receipts, assessment
            )
            (output / "paper_trading_readiness_ledger_v80_04.json").write_text("{}")
            with self.assertRaises(ValueError):
                verify_readiness_manifest(output, stored["manifest"])

    def test_bad_historical_certificate(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "certificate.json"
            path.write_text("{}")
            with self.assertRaises(ValueError):
                validate_historical_completion_certificate(path)

    def test_safety_source(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "alpaca_market_data/paper_trading_readiness_v80_01_05.py"
        ).read_text().lower()
        self.assertNotIn("submit_order(", source)
        self.assertNotIn("tradingclient(", source)
        self.assertNotIn("api_secret", source)
        self.assertNotIn("api_key", source)
        self.assertNotIn("os.getenv", source)

if __name__ == "__main__":
    unittest.main()
