import unittest
from decimal import Decimal

from tools.strategy_analytics_v64_0 import (
    StrategyAnalyticsEngine,
    aggregate_group,
    sha256_hex,
)


def risk(score="0"):
    return {
        "status": "PASS",
        "network_used": False,
        "risk_report_sha256": "c" * 64,
        "analytics": {"risk_score": score},
    }


def history(events=None):
    return {
        "status": "PASS",
        "network_used": False,
        "history_sha256": "d" * 64,
        "trades": events or [],
    }


def closed_trade(
    pnl="100",
    strategy="alpha",
    symbol="AAPL",
    side="LONG",
    opened="2026-07-29T15:00:00Z",
    closed="2026-07-29T16:00:00Z",
):
    return {
        "trade_id": f"{strategy}-{symbol}-{pnl}",
        "strategy": strategy,
        "symbol": symbol,
        "side": side,
        "opened_at": opened,
        "closed_at": closed,
        "realized_pnl": pnl,
        "status": "CLOSED",
    }


class TestV64(unittest.TestCase):
    def engine(self):
        return StrategyAnalyticsEngine()

    def test_status(self):
        self.assertEqual("PASS", self.engine().build(history(), risk())["status"])

    def test_version(self):
        self.assertEqual("64.0", self.engine().build(history(), risk())["version"])

    def test_network_false(self):
        self.assertFalse(self.engine().build(history(), risk())["network_used"])

    def test_empty_history_supported(self):
        r = self.engine().build(history(), risk())
        self.assertEqual(0, r["closed_trade_count"])

    def test_closed_count(self):
        r = self.engine().build(history([closed_trade()]), risk())
        self.assertEqual(1, r["closed_trade_count"])

    def test_open_count(self):
        event = {
            "symbol": "AAPL",
            "side": "LONG",
            "strategy": "alpha",
            "opened_at": "2026-07-29T15:00:00Z",
            "status": "OPEN",
        }
        r = self.engine().build(history([event]), risk())
        self.assertEqual(1, r["open_trade_count"])

    def test_win_rate(self):
        events = [closed_trade("100"), closed_trade("-50", symbol="MSFT")]
        r = self.engine().build(history(events), risk())
        self.assertEqual("0.500000", r["overall"]["win_rate"])

    def test_net_pnl(self):
        events = [closed_trade("100"), closed_trade("-50", symbol="MSFT")]
        r = self.engine().build(history(events), risk())
        self.assertEqual("50.0000", r["overall"]["net_pnl"])

    def test_profit_factor(self):
        events = [closed_trade("100"), closed_trade("-50", symbol="MSFT")]
        r = self.engine().build(history(events), risk())
        self.assertEqual("2.000000", r["overall"]["profit_factor"])

    def test_expectancy(self):
        events = [closed_trade("100"), closed_trade("-50", symbol="MSFT")]
        r = self.engine().build(history(events), risk())
        self.assertEqual("25.0000", r["overall"]["expectancy"])

    def test_average_win(self):
        r = self.engine().build(history([closed_trade("100")]), risk())
        self.assertEqual("100.0000", r["overall"]["average_win"])

    def test_average_loss(self):
        r = self.engine().build(history([closed_trade("-50")]), risk())
        self.assertEqual("-50.0000", r["overall"]["average_loss"])

    def test_payoff_ratio(self):
        events = [closed_trade("100"), closed_trade("-50", symbol="MSFT")]
        r = self.engine().build(history(events), risk())
        self.assertEqual("2.000000", r["overall"]["payoff_ratio"])

    def test_kelly_bounded(self):
        events = [closed_trade("100"), closed_trade("-50", symbol="MSFT")]
        r = self.engine().build(history(events), risk())
        k = Decimal(r["overall"]["kelly_fraction"])
        self.assertGreaterEqual(k, 0)
        self.assertLessEqual(k, 1)

    def test_holding_minutes(self):
        r = self.engine().build(history([closed_trade()]), risk())
        self.assertEqual("60.0000", r["overall"]["average_holding_minutes"])

    def test_strategy_breakdown(self):
        events = [closed_trade("100", strategy="alpha"), closed_trade("50", strategy="beta")]
        r = self.engine().build(history(events), risk())
        self.assertEqual(2, len(r["by_strategy"]))

    def test_symbol_breakdown(self):
        events = [closed_trade("100", symbol="AAPL"), closed_trade("50", symbol="MSFT")]
        r = self.engine().build(history(events), risk())
        self.assertEqual(2, len(r["by_symbol"]))

    def test_side_breakdown(self):
        events = [closed_trade("100", side="LONG"), closed_trade("50", side="SHORT")]
        r = self.engine().build(history(events), risk())
        self.assertEqual(2, len(r["by_side"]))

    def test_weekday_breakdown(self):
        r = self.engine().build(history([closed_trade()]), risk())
        self.assertEqual("Wednesday", r["by_weekday"][0]["group"])

    def test_hour_breakdown(self):
        r = self.engine().build(history([closed_trade()]), risk())
        self.assertEqual("15", r["by_entry_hour_utc"][0]["group"])

    def test_ranking(self):
        events = [
            closed_trade("100", strategy="alpha"),
            closed_trade("20", strategy="beta", symbol="MSFT"),
        ]
        r = self.engine().build(history(events), risk())
        self.assertEqual("alpha", r["strategy_ranking"][0]["strategy"])

    def test_ranking_hash(self):
        r = self.engine().build(history([closed_trade()]), risk())
        self.assertEqual(64, len(r["strategy_ranking"][0]["ranking_sha256"]))

    def test_group_hash(self):
        r = self.engine().build(history([closed_trade()]), risk())
        self.assertEqual(64, len(r["overall"]["group_sha256"]))

    def test_report_hash(self):
        r = self.engine().build(history([closed_trade()]), risk())
        self.assertEqual(64, len(r["strategy_report_sha256"]))

    def test_deterministic(self):
        a = self.engine().build(history([closed_trade()]), risk())
        b = self.engine().build(history([closed_trade()]), risk())
        self.assertEqual(a["strategy_report_sha256"], b["strategy_report_sha256"])

    def test_bad_v60_status(self):
        x = history()
        x["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "v60 status must be PASS"):
            self.engine().build(x, risk())

    def test_bad_v60_network(self):
        x = history()
        x["network_used"] = True
        with self.assertRaisesRegex(ValueError, "v60 network_used must be false"):
            self.engine().build(x, risk())

    def test_bad_history_hash(self):
        x = history()
        x["history_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "64 characters"):
            self.engine().build(x, risk())

    def test_bad_v63_status(self):
        x = risk()
        x["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "v63 status must be PASS"):
            self.engine().build(history(), x)

    def test_bad_v63_network(self):
        x = risk()
        x["network_used"] = True
        with self.assertRaisesRegex(ValueError, "v63 network_used must be false"):
            self.engine().build(history(), x)

    def test_bad_risk_hash(self):
        x = risk()
        x["risk_report_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "64 characters"):
            self.engine().build(history(), x)

    def test_sha(self):
        self.assertEqual(64, len(sha256_hex({"x": 1})))


if __name__ == "__main__":
    unittest.main()
