import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools.daily_performance_journal_v61_0 import (
    DailyPerformanceJournal,
    empty_journal,
    export_csv,
    sha256_hex,
)


def v59(equity="50480", cash="29980", market="20500", unrealized="480", h="a"):
    return {
        "status": "PASS",
        "network_used": False,
        "integration_sha256": h * 64,
        "portfolio": {
            "ending_cash": cash,
            "market_value": market,
            "equity": equity,
            "unrealized_pnl": unrealized,
        },
    }


def v60(trades=1, realized="0", wins=0, losses=0, breaks=0, h="b"):
    return {
        "status": "PASS",
        "network_used": False,
        "history_sha256": h * 64,
        "trade_count": trades,
        "open_lot_count": 1,
        "statistics": {
            "event_count": trades,
            "net_realized_pnl": realized,
            "win_count": wins,
            "loss_count": losses,
            "breakeven_count": breaks,
            "open_lot_count": 1,
            "win_rate": "0.000000",
            "profit_factor": "0.000000",
        },
    }


class TestV61(unittest.TestCase):
    def engine(self):
        return DailyPerformanceJournal()

    def first(self):
        return self.engine().update(v59(), v60(), None, "2026-07-29T22:00:00Z")

    def second(self, equity="51000"):
        return self.engine().update(
            v59(equity=equity, cash="30000", market="21000", unrealized="1000", h="c"),
            v60(trades=2, realized="100", wins=1, h="d"),
            self.first(),
            "2026-07-30T22:00:00Z",
        )

    def test_first_entry(self):
        r = self.first()
        self.assertEqual(1, r["entry_count"])
        self.assertEqual("2026-07-29", r["entries"][0]["journal_date"])

    def test_first_daily_pnl_zero(self):
        self.assertEqual("0.0000", self.first()["entries"][0]["daily_pnl"])

    def test_first_daily_return_zero(self):
        self.assertEqual("0.000000", self.first()["entries"][0]["daily_return"])

    def test_second_daily_pnl(self):
        self.assertEqual("520.0000", self.second()["entries"][-1]["daily_pnl"])

    def test_second_daily_return(self):
        self.assertEqual("0.010301", self.second()["entries"][-1]["daily_return"])

    def test_trade_event_delta(self):
        self.assertEqual(1, self.second()["entries"][-1]["daily_trade_events"])

    def test_closed_trade_delta(self):
        self.assertEqual(1, self.second()["entries"][-1]["daily_closed_trades"])

    def test_hash_chain_genesis(self):
        self.assertEqual("GENESIS", self.first()["entries"][0]["previous_entry_sha256"])

    def test_hash_chain_second(self):
        a = self.first()
        b = self.engine().update(
            v59(h="c"), v60(trades=2, h="d"), a, "2026-07-30T22:00:00Z"
        )
        self.assertEqual(a["entries"][0]["entry_sha256"], b["entries"][1]["previous_entry_sha256"])

    def test_entry_hash_length(self):
        self.assertEqual(64, len(self.first()["entries"][0]["entry_sha256"]))

    def test_journal_hash_length(self):
        self.assertEqual(64, len(self.first()["journal_sha256"]))

    def test_summary_hash_length(self):
        self.assertEqual(64, len(self.first()["summary"]["summary_sha256"]))

    def test_duplicate_date_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate journal_date"):
            self.engine().update(v59(h="c"), v60(h="d"), self.first(), "2026-07-29T23:00:00Z")

    def test_duplicate_v59_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate V59 integration"):
            self.engine().update(v59(), v60(h="d"), self.first(), "2026-07-30T22:00:00Z")

    def test_duplicate_v60_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate V60 history"):
            self.engine().update(v59(h="c"), v60(), self.first(), "2026-07-30T22:00:00Z")

    def test_bad_v59_status(self):
        x = v59()
        x["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "status must be PASS"):
            self.engine().update(x, v60(), None, "2026-07-29T22:00:00Z")

    def test_bad_v60_status(self):
        x = v60()
        x["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "status must be PASS"):
            self.engine().update(v59(), x, None, "2026-07-29T22:00:00Z")

    def test_network_block_v59(self):
        x = v59()
        x["network_used"] = True
        with self.assertRaisesRegex(ValueError, "network_used must be false"):
            self.engine().update(x, v60(), None, "2026-07-29T22:00:00Z")

    def test_network_block_v60(self):
        x = v60()
        x["network_used"] = True
        with self.assertRaisesRegex(ValueError, "network_used must be false"):
            self.engine().update(v59(), x, None, "2026-07-29T22:00:00Z")

    def test_bad_time(self):
        with self.assertRaisesRegex(ValueError, "include timezone"):
            self.engine().update(v59(), v60(), None, "2026-07-29T22:00:00")

    def test_trade_count_cannot_decrease(self):
        first = self.engine().update(v59(), v60(trades=2), None, "2026-07-29T22:00:00Z")
        with self.assertRaisesRegex(ValueError, "cannot decrease"):
            self.engine().update(v59(h="c"), v60(trades=1, h="d"), first, "2026-07-30T22:00:00Z")

    def test_positive_day(self):
        self.assertEqual(1, self.second()["summary"]["positive_day_count"])

    def test_flat_day(self):
        self.assertEqual(1, self.second()["summary"]["flat_day_count"])

    def test_negative_day(self):
        r = self.second(equity="49000")
        self.assertEqual(1, r["summary"]["negative_day_count"])

    def test_best_return(self):
        self.assertEqual("0.010301", self.second()["summary"]["best_daily_return"])

    def test_worst_return(self):
        self.assertEqual("0.000000", self.second()["summary"]["worst_daily_return"])

    def test_cumulative_return(self):
        self.assertEqual("0.010301", self.second()["summary"]["cumulative_return"])

    def test_latest_equity(self):
        self.assertEqual("51000.0000", self.second()["summary"]["latest_equity"])

    def test_deterministic(self):
        a = self.first()
        b = self.first()
        self.assertEqual(a["journal_sha256"], b["journal_sha256"])

    def test_csv_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.csv"
            export_csv(self.second(), path)
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(2, len(rows))
            self.assertEqual("2026-07-30", rows[-1]["journal_date"])

    def test_empty_journal_shape(self):
        x = empty_journal()
        self.assertEqual([], x["entries"])
        self.assertEqual(0, x["entry_count"])

    def test_sha(self):
        self.assertEqual(64, len(sha256_hex({"a": 1})))

    def test_missing_snapshot(self):
        x = v59()
        del x["portfolio"]
        with self.assertRaisesRegex(ValueError, "not found"):
            self.engine().update(x, v60(), None, "2026-07-29T22:00:00Z")

    def test_bad_hash(self):
        x = v59()
        x["integration_sha256"] = "abc"
        with self.assertRaisesRegex(ValueError, "64 characters"):
            self.engine().update(x, v60(), None, "2026-07-29T22:00:00Z")

    def test_official_v59_snapshot_schema(self):
        official = {
            "status": "PASS",
            "network_used": False,
            "integration_sha256": "e" * 64,
            "snapshot": {
                "cash_balance": "29980.0000",
                "total_market_value": "20500.0000",
                "net_liquidation_value": "50480.0000",
                "positions": [
                    {
                        "symbol": "AAPL",
                        "market_value": "20500.0000",
                        "unrealized_pnl": "480.0000",
                    }
                ],
            },
            "reconciliation": {
                "ending_cash": "29980.0000",
                "total_market_value": "20500.0000",
                "total_unrealized_pnl": "480.0000",
                "total_equity": "50480.0000",
            },
        }
        result = self.engine().update(
            official,
            v60(h="f"),
            None,
            "2026-07-29T22:00:00Z",
        )
        entry = result["entries"][0]
        self.assertEqual("29980.0000", entry["cash"])
        self.assertEqual("20500.0000", entry["market_value"])
        self.assertEqual("50480.0000", entry["equity"])
        self.assertEqual("480.0000", entry["unrealized_pnl"])

    def test_snapshot_position_unrealized_fallback(self):
        official = {
            "status": "PASS",
            "network_used": False,
            "integration_sha256": "e" * 64,
            "snapshot": {
                "cash_balance": "1000.0000",
                "total_market_value": "500.0000",
                "net_liquidation_value": "1500.0000",
                "positions": [
                    {"market_value": "500.0000", "unrealized_pnl": "25.0000"}
                ],
            },
        }
        result = self.engine().update(
            official, v60(h="f"), None, "2026-07-29T22:00:00Z"
        )
        self.assertEqual("25.0000", result["entries"][0]["unrealized_pnl"])

    def test_reconciliation_fallback(self):
        official = {
            "status": "PASS",
            "network_used": False,
            "integration_sha256": "e" * 64,
            "reconciliation": {
                "ending_cash": "29980.0000",
                "total_market_value": "20500.0000",
                "total_unrealized_pnl": "480.0000",
                "total_equity": "50480.0000",
                "positions": [],
            },
        }
        result = self.engine().update(
            official, v60(h="f"), None, "2026-07-29T22:00:00Z"
        )
        entry = result["entries"][0]
        self.assertEqual("50480.0000", entry["equity"])
        self.assertEqual("480.0000", entry["unrealized_pnl"])

    def test_version(self):
        self.assertEqual("61.1", self.first()["version"])

    def test_status(self):
        self.assertEqual("PASS", self.first()["status"])

    def test_network_false(self):
        self.assertFalse(self.first()["network_used"])


if __name__ == "__main__":
    unittest.main()
