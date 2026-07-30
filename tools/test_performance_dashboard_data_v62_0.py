import csv
import tempfile
import unittest
from pathlib import Path

from tools.performance_dashboard_data_v62_0 import (
    PerformanceDashboardBuilder,
    export_chart_csv,
    sha256_hex,
)


def journal(equities=None, returns=None, pnls=None):
    equities = equities or ["50480.0000"]
    returns = returns or ["0.000000"] * len(equities)
    pnls = pnls or ["0.0000"] * len(equities)
    entries = []
    for i, equity in enumerate(equities):
        entries.append({
            "sequence": i + 1,
            "journal_date": f"2026-07-{29+i:02d}",
            "equity": equity,
            "daily_pnl": pnls[i],
            "daily_return": returns[i],
            "trade_count": i + 1,
            "daily_trade_events": 1,
            "closed_trade_count": i,
            "daily_closed_trades": 1 if i else 0,
        })
    return {
        "status": "PASS",
        "network_used": False,
        "journal_sha256": "a" * 64,
        "entries": entries,
    }


class TestV62(unittest.TestCase):
    def engine(self):
        return PerformanceDashboardBuilder()

    def test_single_point(self):
        r = self.engine().build(journal())
        self.assertEqual(1, r["chart_point_count"])

    def test_single_equity(self):
        self.assertEqual("50480.0000", self.engine().build(journal())["metrics"]["latest_equity"])

    def test_total_return(self):
        r = self.engine().build(journal(["50000", "51000"], ["0", "0.02"], ["0", "1000"]))
        self.assertEqual("0.020000", r["metrics"]["total_return"])

    def test_total_pnl(self):
        r = self.engine().build(journal(["50000", "51000"], ["0", "0.02"], ["0", "1000"]))
        self.assertEqual("1000.0000", r["metrics"]["total_pnl"])

    def test_running_peak(self):
        r = self.engine().build(journal(["50000", "51000", "50500"]))
        self.assertEqual("51000.0000", r["chart"][-1]["running_peak"])

    def test_drawdown(self):
        r = self.engine().build(journal(["50000", "51000", "45900"]))
        self.assertEqual("-0.100000", r["chart"][-1]["drawdown"])

    def test_max_drawdown(self):
        r = self.engine().build(journal(["50000", "51000", "45900"]))
        self.assertEqual("-0.100000", r["metrics"]["max_drawdown"])

    def test_max_drawdown_date(self):
        r = self.engine().build(journal(["50000", "51000", "45900"]))
        self.assertEqual("2026-07-31", r["metrics"]["max_drawdown_date"])

    def test_positive_days(self):
        r = self.engine().build(journal(["50000", "51000"], ["0", "0.02"]))
        self.assertEqual(1, r["metrics"]["positive_day_count"])

    def test_negative_days(self):
        r = self.engine().build(journal(["50000", "49000"], ["0", "-0.02"]))
        self.assertEqual(1, r["metrics"]["negative_day_count"])

    def test_flat_days(self):
        self.assertEqual(1, self.engine().build(journal())["metrics"]["flat_day_count"])

    def test_profitable_ratio(self):
        r = self.engine().build(journal(["50000", "51000"], ["0", "0.02"]))
        self.assertEqual("0.500000", r["metrics"]["profitable_day_ratio"])

    def test_recent_window(self):
        r = self.engine().build(journal(["1", "2", "3", "4", "5", "6"]), recent_days=5)
        self.assertEqual(5, r["recent_summary"]["window_days_used"])

    def test_recent_pnl(self):
        r = self.engine().build(journal(["100", "110", "120"]), recent_days=2)
        self.assertEqual("10.0000", r["recent_summary"]["pnl"])

    def test_recent_return(self):
        r = self.engine().build(journal(["100", "110", "121"]), recent_days=2)
        self.assertEqual("0.100000", r["recent_summary"]["return"])

    def test_recent_trade_events(self):
        r = self.engine().build(journal(["100", "110", "121"]), recent_days=2)
        self.assertEqual(2, r["recent_summary"]["trade_events"])

    def test_recent_closed_trades(self):
        r = self.engine().build(journal(["100", "110", "121"]), recent_days=2)
        self.assertEqual(2, r["recent_summary"]["closed_trades"])

    def test_status(self):
        self.assertEqual("PASS", self.engine().build(journal())["status"])

    def test_version(self):
        self.assertEqual("62.0", self.engine().build(journal())["version"])

    def test_network_false(self):
        self.assertFalse(self.engine().build(journal())["network_used"])

    def test_bad_status(self):
        x = journal()
        x["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "status must be PASS"):
            self.engine().build(x)

    def test_network_rejected(self):
        x = journal()
        x["network_used"] = True
        with self.assertRaisesRegex(ValueError, "network_used must be false"):
            self.engine().build(x)

    def test_empty_entries_rejected(self):
        x = journal()
        x["entries"] = []
        with self.assertRaisesRegex(ValueError, "non-empty list"):
            self.engine().build(x)

    def test_bad_hash_rejected(self):
        x = journal()
        x["journal_sha256"] = "abc"
        with self.assertRaisesRegex(ValueError, "64 characters"):
            self.engine().build(x)

    def test_recent_days_zero(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            self.engine().build(journal(), recent_days=0)

    def test_point_hash(self):
        self.assertEqual(64, len(self.engine().build(journal())["chart"][0]["point_sha256"]))

    def test_metrics_hash(self):
        self.assertEqual(64, len(self.engine().build(journal())["metrics"]["metrics_sha256"]))

    def test_recent_hash(self):
        self.assertEqual(64, len(self.engine().build(journal())["recent_summary"]["recent_sha256"]))

    def test_dashboard_hash(self):
        self.assertEqual(64, len(self.engine().build(journal())["dashboard_sha256"]))

    def test_deterministic(self):
        a = self.engine().build(journal())
        b = self.engine().build(journal())
        self.assertEqual(a["dashboard_sha256"], b["dashboard_sha256"])

    def test_csv_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dashboard.csv"
            result = self.engine().build(journal(["50000", "51000"]))
            export_chart_csv(result, path)
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(2, len(rows))
            self.assertEqual("51000.0000", rows[-1]["equity"])

    def test_sha(self):
        self.assertEqual(64, len(sha256_hex({"x": 1})))


if __name__ == "__main__":
    unittest.main()
