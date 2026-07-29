import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "position_manager_v37_0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "position_manager_v37_0",
    MODULE_PATH,
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class PositionManagerV370Tests(unittest.TestCase):
    def test_open_long_position(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="buy",
            quantity="10",
            price="200",
        )
        snap = manager.snapshot()
        self.assertEqual(snap.side, "long")
        self.assertEqual(snap.quantity, "10")
        self.assertEqual(snap.average_price, "200")

    def test_long_average_price(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="buy",
            quantity="4",
            price="200",
        )
        manager.apply_fill(
            trade_side="buy",
            quantity="6",
            price="210",
        )
        self.assertEqual(manager.snapshot().average_price, "206")

    def test_long_partial_close_realized_pnl(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="buy",
            quantity="10",
            price="200",
        )
        manager.apply_fill(
            trade_side="sell",
            quantity="4",
            price="210",
        )
        snap = manager.snapshot()
        self.assertEqual(snap.quantity, "6")
        self.assertEqual(snap.realized_pnl, "40")
        self.assertEqual(snap.side, "long")

    def test_long_full_close(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="buy",
            quantity="10",
            price="200",
        )
        manager.apply_fill(
            trade_side="sell",
            quantity="10",
            price="210",
        )
        snap = manager.snapshot()
        self.assertTrue(snap.closed)
        self.assertEqual(snap.side, "flat")
        self.assertEqual(snap.realized_pnl, "100")

    def test_unrealized_pnl_long(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="buy",
            quantity="10",
            price="200",
        )
        manager.mark_price("212")
        self.assertEqual(manager.snapshot().unrealized_pnl, "120")

    def test_open_short_position(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="sell",
            quantity="5",
            price="200",
        )
        snap = manager.snapshot()
        self.assertEqual(snap.side, "short")
        self.assertEqual(snap.quantity, "5")

    def test_short_realized_pnl(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="sell",
            quantity="5",
            price="200",
        )
        manager.apply_fill(
            trade_side="buy",
            quantity="2",
            price="190",
        )
        self.assertEqual(manager.snapshot().realized_pnl, "20")

    def test_position_flip_long_to_short(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="buy",
            quantity="5",
            price="200",
        )
        manager.apply_fill(
            trade_side="sell",
            quantity="8",
            price="210",
        )
        snap = manager.snapshot()
        self.assertEqual(snap.side, "short")
        self.assertEqual(snap.quantity, "3")
        self.assertEqual(snap.average_price, "210")
        self.assertEqual(snap.realized_pnl, "50")

    def test_position_flip_short_to_long(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="sell",
            quantity="5",
            price="200",
        )
        manager.apply_fill(
            trade_side="buy",
            quantity="8",
            price="190",
        )
        snap = manager.snapshot()
        self.assertEqual(snap.side, "long")
        self.assertEqual(snap.quantity, "3")
        self.assertEqual(snap.average_price, "190")
        self.assertEqual(snap.realized_pnl, "50")

    def test_event_hashes(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="buy",
            quantity="1",
            price="200",
        )
        self.assertEqual(len(manager.ledger()[0].event_sha256), 64)

    def test_snapshot_hash(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="buy",
            quantity="1",
            price="200",
        )
        self.assertEqual(len(manager.snapshot().snapshot_sha256), 64)

    def test_export_no_network(self):
        manager = MOD.PositionManager("AAPL")
        manager.apply_fill(
            trade_side="buy",
            quantity="1",
            price="200",
        )
        self.assertFalse(manager.export()["network_used"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
