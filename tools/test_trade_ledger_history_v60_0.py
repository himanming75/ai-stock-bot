import tempfile
import unittest
from pathlib import Path
from tools.trade_ledger_history_v60_0 import TradeLedgerHistoryV600, canonical_hash, write_csv

def v59(action="BUY", event_type="POSITION_OPENED", quantity="100", price="200.2000", pnl="0.0000"):
    return {
        "status": "PASS",
        "network_used": False,
        "execution_sha256": "a" * 64,
        "integration_sha256": "b" * 64,
        "reconciliation": {
            "ledger": [{
                "symbol": "AAPL",
                "action": action,
                "event_type": event_type,
                "quantity": quantity,
                "price": price,
                "commission": "0.0000",
                "realized_pnl_delta": pnl,
            }]
        }
    }

def empty_history():
    return {"trades": [], "open_lots": [], "network_used": False}

class TestV60(unittest.TestCase):
    def engine(self):
        return TradeLedgerHistoryV600()

    def open_result(self):
        return self.engine().update(
            v59(),
            empty_history(),
            event_time="2026-07-29T22:00:00Z",
        )

    def next_v59(self, *args):
        data = v59(*args)
        data["execution_sha256"] = "c" * 64
        data["integration_sha256"] = "d" * 64
        return data

    def test_open_buy(self):
        r = self.open_result()
        self.assertEqual("OPEN", r["trades"][0]["trade_outcome"])

    def test_open_lot_created(self):
        self.assertEqual(1, self.open_result()["open_lot_count"])

    def test_trade_count(self):
        self.assertEqual(1, self.open_result()["trade_count"])

    def test_trade_id_prefix(self):
        self.assertTrue(self.open_result()["latest_trade_id"].startswith("TRD-"))

    def test_history_hash(self):
        self.assertEqual(64, len(self.open_result()["history_sha256"]))

    def test_entry_hash(self):
        self.assertEqual(64, len(self.open_result()["trades"][0]["entry_sha256"]))

    def test_lot_hash(self):
        self.assertEqual(64, len(self.open_result()["open_lots"][0]["lot_sha256"]))

    def test_genesis(self):
        self.assertEqual("GENESIS", self.open_result()["trades"][0]["previous_entry_sha256"])

    def test_stats_zero_closed(self):
        self.assertEqual("0.000000", self.open_result()["statistics"]["win_rate"])

    def test_close_win(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_CLOSED", "100", "205.0000", "480.0000"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual("WIN", r["trades"][-1]["trade_outcome"])
        self.assertEqual(1, r["statistics"]["win_count"])

    def test_close_loss(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_CLOSED", "100", "195.0000", "-520.0000"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual("LOSS", r["trades"][-1]["trade_outcome"])

    def test_close_breakeven(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_CLOSED", "100", "200.2000", "0"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual("BREAKEVEN", r["trades"][-1]["trade_outcome"])

    def test_partial_close_keeps_lot(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_REDUCED", "40", "205", "192"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual("60", r["open_lots"][0]["remaining_quantity"])

    def test_close_removes_lot(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_CLOSED", "100", "205", "480"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual(0, r["open_lot_count"])

    def test_average_entry_price(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_CLOSED", "100", "205", "480"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual("200.2000", r["trades"][-1]["average_entry_price"])

    def test_holding_period(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_CLOSED", "100", "205", "480"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual(86400, r["trades"][-1]["holding_period_seconds"])

    def test_profit_factor_inf(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_CLOSED", "100", "205", "480"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual("INF", r["statistics"]["profit_factor"])

    def test_expectancy(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_CLOSED", "100", "205", "480"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual("480.0000", r["statistics"]["expectancy"])

    def test_chain(self):
        first = self.open_result()
        r = self.engine().update(
            self.next_v59("SELL", "POSITION_CLOSED", "100", "205", "480"),
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual(
            r["trades"][0]["entry_sha256"],
            r["trades"][1]["previous_entry_sha256"],
        )

    def test_deterministic(self):
        self.assertEqual(
            self.open_result()["history_sha256"],
            self.open_result()["history_sha256"],
        )

    def test_bad_status(self):
        data = v59()
        data["status"] = "FAIL"
        with self.assertRaises(ValueError):
            self.engine().update(data, empty_history(), event_time="2026-07-29T22:00:00Z")

    def test_network_rejected(self):
        data = v59()
        data["network_used"] = True
        with self.assertRaises(ValueError):
            self.engine().update(data, empty_history(), event_time="2026-07-29T22:00:00Z")

    def test_bad_action(self):
        with self.assertRaises(ValueError):
            self.engine().update(v59("HOLD"), empty_history(), event_time="2026-07-29T22:00:00Z")

    def test_bad_event_type(self):
        with self.assertRaises(ValueError):
            self.engine().update(v59(event_type="UNKNOWN"), empty_history(), event_time="2026-07-29T22:00:00Z")

    def test_zero_quantity(self):
        with self.assertRaises(ValueError):
            self.engine().update(v59(quantity="0"), empty_history(), event_time="2026-07-29T22:00:00Z")

    def test_sell_without_lot(self):
        with self.assertRaises(ValueError):
            self.engine().update(
                self.next_v59("SELL", "POSITION_CLOSED", "100", "205", "480"),
                empty_history(),
                event_time="2026-07-30T22:00:00Z",
            )

    def test_oversell(self):
        first = self.open_result()
        with self.assertRaises(ValueError):
            self.engine().update(
                self.next_v59("SELL", "POSITION_CLOSED", "101", "205", "480"),
                first,
                event_time="2026-07-30T22:00:00Z",
            )

    def test_live_blocked(self):
        with self.assertRaises(PermissionError):
            TradeLedgerHistoryV600(mode="live").update(
                v59(),
                empty_history(),
                event_time="2026-07-29T22:00:00Z",
            )

    def test_live_unimplemented(self):
        with self.assertRaises(NotImplementedError):
            TradeLedgerHistoryV600(mode="live", enable_live=True).update(
                v59(),
                empty_history(),
                event_time="2026-07-29T22:00:00Z",
            )

    def test_duplicate_trade_id_rejected(self):
        bad = {"trades": [{"trade_id": "X"}, {"trade_id": "X"}], "open_lots": [], "network_used": False}
        with self.assertRaises(ValueError):
            self.engine().update(v59(), bad, event_time="2026-07-29T22:00:00Z")

    def test_csv_export(self):
        result = self.open_result()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "history.csv"
            write_csv(path, result["trades"])
            self.assertTrue(path.exists())
            self.assertIn("trade_id", path.read_text(encoding="utf-8-sig"))

    def test_duplicate_execution_sha_rejected(self):
        first = self.open_result()
        with self.assertRaisesRegex(ValueError, "duplicate execution_sha256"):
            self.engine().update(
                v59(),
                first,
                event_time="2026-07-30T22:00:00Z",
            )

    def test_duplicate_integration_sha_rejected(self):
        first = self.open_result()
        second_input = v59()
        second_input["execution_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "duplicate v59_integration_sha256"):
            self.engine().update(
                second_input,
                first,
                event_time="2026-07-30T22:00:00Z",
            )

    def test_new_execution_and_integration_allowed(self):
        first = self.open_result()
        second_input = v59("BUY", "POSITION_INCREASED", "50", "210", "0")
        second_input["execution_sha256"] = "c" * 64
        second_input["integration_sha256"] = "d" * 64
        result = self.engine().update(
            second_input,
            first,
            event_time="2026-07-30T22:00:00Z",
        )
        self.assertEqual(2, result["trade_count"])

    def test_statistics_hash(self):
        self.assertEqual(64, len(self.open_result()["statistics"]["statistics_sha256"]))

    def test_fifo_multiple_lots(self):
        first = self.open_result()
        second_input = v59("BUY", "POSITION_INCREASED", "50", "210", "0")
        second_input["execution_sha256"] = "c" * 64
        second_input["integration_sha256"] = "d" * 64
        second = self.engine().update(
            second_input,
            first,
            event_time="2026-07-30T10:00:00Z",
        )
        close_input = v59("SELL", "POSITION_REDUCED", "120", "220", "0")
        close_input["execution_sha256"] = "e" * 64
        close_input["integration_sha256"] = "f" * 64
        closed = self.engine().update(
            close_input,
            second,
            event_time="2026-07-31T10:00:00Z",
        )
        self.assertEqual("30", closed["open_lots"][0]["remaining_quantity"])
        self.assertEqual(2, len(closed["trades"][-1]["matched_lot_ids"]))

if __name__ == "__main__":
    unittest.main()
