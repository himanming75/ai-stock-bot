import json
import tempfile
import unittest
from pathlib import Path

from final_production_release.config import load, validate
from final_production_release.engine import evaluate
from final_production_release.integration import evaluate as integration
from final_production_release.integrity import build as integrity
from final_production_release.inventory import build


class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as temp:
            config = load(Path(temp))
            self.assertFalse(
                config["automatic_order_submission_enabled"]
            )
            self.assertFalse(config["broker_write_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertTrue(validate(load(Path(temp)))["valid"])

    def test_inventory_live_zero_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            result = build(Path(temp))
            self.assertEqual(
                result["total_actual_live_orders_submitted"],
                0,
            )

    def test_inventory_detects_live_order(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "release/v120_final/actual"
            output.mkdir(parents=True)
            (output / "v120_final_release_result.json").write_text(
                json.dumps({"actual_live_orders_submitted": 1}),
                encoding="utf-8",
            )
            self.assertEqual(
                build(root)["total_actual_live_orders_submitted"],
                1,
            )

    def test_v160_actual_health_status_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = (
                root
                / "release/v156_01_to_v160_64/actual"
            )
            output.mkdir(parents=True)
            (output / "health_status.json").write_text(
                json.dumps({
                    "state": "OPERATIONS_HEALTHY",
                    "actual_live_orders_submitted": 0,
                }),
                encoding="utf-8",
            )

            inventory = build(root)
            row = next(
                item
                for item in inventory["rows"]
                if item["stage"] == "V160_OPERATIONS"
            )

            self.assertTrue(row["present"])
            self.assertEqual(
                row["path"],
                "release/v156_01_to_v160_64/"
                "actual/health_status.json",
            )

    def test_v160_legacy_fallback_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = (
                root
                / "release/v156_01_to_v160_64/actual"
            )
            output.mkdir(parents=True)
            (
                output
                / "operations_center_verification.json"
            ).write_text(
                json.dumps({
                    "state": "OPERATIONS_READY",
                    "actual_live_orders_submitted": 0,
                }),
                encoding="utf-8",
            )

            inventory = build(root)
            row = next(
                item
                for item in inventory["rows"]
                if item["stage"] == "V160_OPERATIONS"
            )

            self.assertTrue(row["present"])
            self.assertEqual(
                row["path"],
                "release/v156_01_to_v160_64/"
                "actual/operations_center_verification.json",
            )

    def test_integration_reports_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(
                integration(Path(temp))["all_modules_present"]
            )

    def test_integrity_reports_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(
                integrity(Path(temp))["all_present"]
            )

    def test_engine_never_enables_live(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate(
                Path(temp),
                create_release_bundle=False,
            )
            self.assertFalse(result["live_trading_ready"])
            self.assertFalse(result["broker_write_enabled"])

    def test_engine_live_zero_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate(Path(temp), False)
            self.assertEqual(
                result["actual_live_orders_submitted"],
                0,
            )


if __name__ == "__main__":
    unittest.main()
