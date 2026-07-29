import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "partial_fill_engine_v36_2.py"
)
SPEC = importlib.util.spec_from_file_location(
    "partial_fill_engine_v36_2",
    MODULE_PATH,
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class PartialFillEngineV362Tests(unittest.TestCase):
    def make_engine(self):
        return MOD.PartialFillEngine(
            order_id="order-test-001",
            symbol="AAPL",
            side="buy",
            order_quantity="10",
        )

    def test_first_partial_fill(self):
        engine = self.make_engine()
        receipt = engine.apply_fill(
            trade_id="trade-001",
            quantity="4",
            price="200",
        )
        self.assertEqual(receipt.status, "PARTIALLY_FILLED")
        self.assertEqual(receipt.cumulative_quantity, "4")
        self.assertEqual(receipt.remaining_quantity, "6")
        self.assertEqual(receipt.cumulative_vwap, "200")

    def test_multiple_fills_vwap(self):
        engine = self.make_engine()
        engine.apply_fill(
            trade_id="trade-001",
            quantity="4",
            price="200",
        )
        receipt = engine.apply_fill(
            trade_id="trade-002",
            quantity="6",
            price="210",
        )
        self.assertEqual(receipt.status, "FILLED")
        self.assertEqual(receipt.cumulative_quantity, "10")
        self.assertEqual(receipt.remaining_quantity, "0")
        self.assertEqual(receipt.cumulative_vwap, "206")
        self.assertTrue(engine.snapshot().complete)

    def test_duplicate_trade_id_rejected(self):
        engine = self.make_engine()
        engine.apply_fill(
            trade_id="trade-001",
            quantity="4",
            price="200",
        )
        duplicate = engine.apply_fill(
            trade_id="trade-001",
            quantity="1",
            price="201",
        )
        self.assertEqual(
            duplicate.status,
            "REJECTED_DUPLICATE_TRADE_ID",
        )
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(len(engine.ledger()), 1)

    def test_overfill_rejected(self):
        engine = self.make_engine()
        receipt = engine.apply_fill(
            trade_id="trade-001",
            quantity="11",
            price="200",
        )
        self.assertEqual(receipt.status, "REJECTED_OVERFILL")
        self.assertEqual(len(engine.ledger()), 0)

    def test_fill_records_have_hashes(self):
        engine = self.make_engine()
        engine.apply_fill(
            trade_id="trade-001",
            quantity="4",
            price="200",
        )
        record = engine.ledger()[0]
        self.assertEqual(len(record.fill_sha256), 64)

    def test_receipts_have_hashes(self):
        engine = self.make_engine()
        receipt = engine.apply_fill(
            trade_id="trade-001",
            quantity="4",
            price="200",
        )
        self.assertEqual(len(receipt.receipt_sha256), 64)

    def test_export_contains_no_network_usage(self):
        engine = self.make_engine()
        engine.apply_fill(
            trade_id="trade-001",
            quantity="4",
            price="200",
        )
        payload = engine.export()
        self.assertFalse(payload["network_used"])
        self.assertEqual(payload["snapshot"]["fill_count"], 1)

    def test_weighted_vwap_decimal(self):
        engine = MOD.PartialFillEngine(
            order_id="order-test-002",
            symbol="MSFT",
            side="buy",
            order_quantity="3",
        )
        engine.apply_fill(
            trade_id="trade-a",
            quantity="1",
            price="100",
        )
        engine.apply_fill(
            trade_id="trade-b",
            quantity="2",
            price="101.5",
        )
        self.assertEqual(engine.vwap(), "101")


if __name__ == "__main__":
    unittest.main(verbosity=2)
