from pathlib import Path
from tempfile import TemporaryDirectory
import json, unittest
from alpaca_market_data.historical_backtest_completion_v79_96_v80_00 import *

def make_certificate(path: Path, stage: str):
    document = {
        "stage": stage,
        "status": "PASS",
        "actual_orders_submitted": 0,
        "trading_client_created": False,
        "credentials_used": 0,
        "network_requests_executed": 0,
    }
    document["certificate_sha256"] = sha256_completion_json(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document))
    return document

class Tests(unittest.TestCase):
    def setUp(self):
        self.config = BacktestCompletionConfig()

    def test_config(self):
        self.config.validate()

    def test_network_rejected(self):
        with self.assertRaises(ValueError):
            BacktestCompletionConfig(allow_network=True).validate()

    def test_certificate_valid(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "certificate.json"
            make_certificate(path, "V79.65")
            self.assertEqual(
                validate_certificate(path, "V79.65")["status"], "PASS"
            )

    def test_certificate_stage_rejected(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "certificate.json"
            make_certificate(path, "V79.70")
            with self.assertRaises(ValueError):
                validate_certificate(path, "V79.65")

    def test_certificate_tamper_rejected(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "certificate.json"
            document = make_certificate(path, "V79.65")
            document["status"] = "FAIL"
            path.write_text(json.dumps(document))
            with self.assertRaises(ValueError):
                validate_certificate(path, "V79.65")

    def test_certificate_order_rejected(self):
        config = BacktestCompletionConfig(
            required_stages=(
                "V79.70", "V79.65", "V79.75", "V79.80",
                "V79.85", "V79.90", "V79.95",
            )
        )
        with self.assertRaises(ValueError):
            config.validate()

    def test_ledger(self):
        chain = [{"stage": stage, "status": "PASS"} for stage in self.config.required_stages]
        summary = {"status": "PASS"}
        ledger = build_completion_ledger(chain, summary)
        self.assertEqual(ledger["chain_length"], 7)
        self.assertEqual(len(ledger["ledger_sha256"]), 64)

    def test_store_reuse(self):
        with TemporaryDirectory() as temp:
            output = Path(temp)
            summary = {"stage": "V79.96", "status": "PASS"}
            ledger = build_completion_ledger(
                [{"stage": "V79.65", "status": "PASS"}], summary
            )
            store_completion_package(output, summary, ledger)
            second = store_completion_package(output, summary, ledger)
            self.assertTrue(second["reused_existing_package"])

    def test_manifest(self):
        with TemporaryDirectory() as temp:
            output = Path(temp)
            summary = {"stage": "V79.96", "status": "PASS"}
            ledger = build_completion_ledger(
                [{"stage": "V79.65", "status": "PASS"}], summary
            )
            stored = store_completion_package(output, summary, ledger)
            self.assertTrue(
                verify_completion_manifest(output, stored["manifest"])
            )

    def test_manifest_tamper(self):
        with TemporaryDirectory() as temp:
            output = Path(temp)
            summary = {"stage": "V79.96", "status": "PASS"}
            ledger = build_completion_ledger(
                [{"stage": "V79.65", "status": "PASS"}], summary
            )
            stored = store_completion_package(output, summary, ledger)
            (output / "historical_backtest_completion_ledger.json").write_text("{}")
            with self.assertRaises(ValueError):
                verify_completion_manifest(output, stored["manifest"])

    def test_report_flags(self):
        with TemporaryDirectory() as temp:
            output = Path(temp)
            summary = {"stage": "V79.96", "status": "PASS"}
            ledger = build_completion_ledger(
                [{"stage": "V79.65", "status": "PASS"}], summary
            )
            stored = store_completion_package(output, summary, ledger)
            self.assertTrue(stored["report"]["historical_engine_complete"])
            self.assertFalse(stored["report"]["live_trading_enabled"])

    def test_summary_hash_changes(self):
        first = build_completion_ledger([], {"value": 1})
        second = build_completion_ledger([], {"value": 2})
        self.assertNotEqual(first["summary_sha256"], second["summary_sha256"])

    def test_orders_rejected(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "certificate.json"
            document = make_certificate(path, "V79.65")
            unsigned = dict(document)
            unsigned.pop("certificate_sha256")
            unsigned["actual_orders_submitted"] = 1
            unsigned["certificate_sha256"] = sha256_completion_json(unsigned)
            path.write_text(json.dumps(unsigned))
            with self.assertRaises(ValueError):
                validate_certificate(path, "V79.65")

    def test_missing_certificate(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                validate_certificate(Path(temp) / "missing.json", "V79.65")

    def test_safety_source(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "alpaca_market_data/historical_backtest_completion_v79_96_v80_00.py"
        ).read_text().lower()
        self.assertNotIn("submit_order(", source)
        self.assertNotIn("tradingclient(", source)
        self.assertNotIn("api_secret", source)

if __name__ == "__main__":
    unittest.main()
