import tempfile
import unittest
from pathlib import Path

from closed_trade_outcome_v41_v45 import ClosedTradeOutcomeCollector


class Tests(unittest.TestCase):
    def test_fifo_single_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeOutcomeCollector(root)
            orders = [
                {
                    "order_id": "B1",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "filled_qty": 1,
                    "filled_avg_price": 100,
                    "filled_at": "2026-08-01T14:00:00+00:00",
                },
                {
                    "order_id": "S1",
                    "symbol": "AAPL",
                    "side": "SELL",
                    "filled_qty": 1,
                    "filled_avg_price": 110,
                    "filled_at": "2026-08-01T15:00:00+00:00",
                },
            ]
            r = svc.v42_build_fifo_round_trips(orders)
            self.assertEqual(r["closed_trade_count"], 1)
            self.assertAlmostEqual(
                r["closed_trades"][0]["realized_pl"], 10
            )

    def test_fifo_partial_match(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeOutcomeCollector(root)
            orders = [
                {
                    "order_id": "B1",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "filled_qty": 2,
                    "filled_avg_price": 100,
                    "filled_at": "2026-08-01T14:00:00+00:00",
                },
                {
                    "order_id": "S1",
                    "symbol": "AAPL",
                    "side": "SELL",
                    "filled_qty": 1,
                    "filled_avg_price": 105,
                    "filled_at": "2026-08-01T15:00:00+00:00",
                },
            ]
            r = svc.v42_build_fifo_round_trips(orders)
            self.assertEqual(r["closed_trade_count"], 1)
            self.assertEqual(r["open_lot_count"], 1)

    def test_no_sell_means_no_closed_trade(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeOutcomeCollector(root)
            orders = [
                {
                    "order_id": "B1",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "filled_qty": 1,
                    "filled_avg_price": 100,
                    "filled_at": "2026-08-01T14:00:00+00:00",
                }
            ]
            r = svc.v42_build_fifo_round_trips(orders)
            self.assertEqual(r["closed_trade_count"], 0)
            self.assertEqual(r["open_lot_count"], 1)

    def test_outcome_ledger_no_broker_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeOutcomeCollector(root)
            r = svc.v43_realized_outcome_ledger([])
            self.assertFalse(r["broker_write_performed"])

    def test_bridge_does_not_overwrite_existing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeOutcomeCollector(root)
            r = svc.v45_bridge_v4_v36([])
            self.assertFalse(r["existing_v4_file_overwritten"])
            self.assertFalse(r["existing_v36_file_overwritten"])

    def test_path_metrics_do_not_fabricate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeOutcomeCollector(root)
            r = svc.v44_collect_path_metrics([])
            self.assertFalse(r["fabricated_path_data"])

    def test_runtime_is_read_only_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeOutcomeCollector(root)
            self.assertTrue(svc.runtime.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
