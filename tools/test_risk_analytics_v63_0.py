import unittest
from decimal import Decimal

from tools.risk_analytics_v63_0 import (
    RiskAnalyticsEngine,
    historical_quantile,
    sha256_hex,
)


def dashboard(returns=None, equities=None, drawdowns=None):
    returns = returns or ["0.000000"]
    equities = equities or ["50480.0000"] * len(returns)
    drawdowns = drawdowns or ["0.000000"] * len(returns)

    chart = []
    peak = Decimal("0")
    for i, (ret, eq, dd) in enumerate(zip(returns, equities, drawdowns)):
        eqd = Decimal(eq)
        peak = max(peak, eqd)
        chart.append({
            "sequence": i + 1,
            "journal_date": f"2026-07-{29+i:02d}",
            "equity": eq,
            "daily_return": ret,
            "running_peak": str(peak),
            "drawdown_amount": str(eqd - peak),
            "drawdown": dd,
        })

    start = Decimal(equities[0])
    end = Decimal(equities[-1])
    total_pnl = end - start
    total_return = total_pnl / start if start else Decimal("0")
    max_dd = min(Decimal(x) for x in drawdowns)

    return {
        "status": "PASS",
        "network_used": False,
        "dashboard_sha256": "b" * 64,
        "chart": chart,
        "metrics": {
            "starting_equity": str(start),
            "latest_equity": str(end),
            "total_pnl": str(total_pnl),
            "total_return": str(total_return),
            "max_drawdown": str(max_dd),
        },
    }


class TestV63(unittest.TestCase):
    def engine(self):
        return RiskAnalyticsEngine()

    def test_status(self):
        self.assertEqual("PASS", self.engine().build(dashboard())["status"])

    def test_version(self):
        self.assertEqual("63.0", self.engine().build(dashboard())["version"])

    def test_network_false(self):
        self.assertFalse(self.engine().build(dashboard())["network_used"])

    def test_observation_count(self):
        r = self.engine().build(dashboard(["0", "0.01", "-0.02"]))
        self.assertEqual(3, r["analytics"]["observation_count"])

    def test_average_return(self):
        r = self.engine().build(dashboard(["0.01", "0.03"]))
        self.assertEqual("0.020000", r["analytics"]["average_daily_return"])

    def test_zero_volatility(self):
        r = self.engine().build(dashboard(["0", "0"]))
        self.assertEqual("0.000000", r["analytics"]["daily_volatility"])

    def test_positive_volatility(self):
        r = self.engine().build(dashboard(["0.01", "-0.01"]))
        self.assertGreater(Decimal(r["analytics"]["daily_volatility"]), 0)

    def test_downside_deviation(self):
        r = self.engine().build(dashboard(["0.01", "-0.02"]))
        self.assertGreater(Decimal(r["analytics"]["downside_deviation_daily"]), 0)

    def test_sharpe_zero_when_no_volatility(self):
        r = self.engine().build(dashboard(["0", "0"]))
        self.assertEqual("0.000000", r["analytics"]["sharpe_ratio"])

    def test_sortino_zero_when_no_downside(self):
        r = self.engine().build(dashboard(["0.01", "0.02"]))
        self.assertEqual("0.000000", r["analytics"]["sortino_ratio"])

    def test_calmar(self):
        r = self.engine().build(
            dashboard(["0", "0.1"], ["100", "110"], ["0", "-0.05"])
        )
        self.assertEqual("2.000000", r["analytics"]["calmar_ratio"])

    def test_recovery_factor(self):
        r = self.engine().build(
            dashboard(["0", "0.1"], ["100", "110"], ["0", "-0.05"])
        )
        self.assertEqual("2.000000", r["analytics"]["recovery_factor"])

    def test_var_loss_nonnegative(self):
        r = self.engine().build(dashboard(["-0.03", "-0.01", "0.02"]))
        self.assertGreaterEqual(Decimal(r["analytics"]["historical_var_loss"]), 0)

    def test_cvar_loss_nonnegative(self):
        r = self.engine().build(dashboard(["-0.03", "-0.01", "0.02"]))
        self.assertGreaterEqual(Decimal(r["analytics"]["historical_cvar_loss"]), 0)

    def test_negative_count(self):
        r = self.engine().build(dashboard(["-0.03", "-0.01", "0.02"]))
        self.assertEqual(2, r["analytics"]["negative_return_count"])

    def test_risk_score_range(self):
        r = self.engine().build(dashboard(["-0.03", "-0.01", "0.02"]))
        score = Decimal(r["analytics"]["risk_score"])
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_low_risk_level(self):
        r = self.engine().build(dashboard())
        self.assertEqual("LOW", r["analytics"]["risk_level"])

    def test_high_or_critical_risk_level(self):
        r = self.engine().build(
            dashboard(["0", "-0.20"], ["100", "80"], ["0", "-0.20"])
        )
        self.assertIn(r["analytics"]["risk_level"], {"HIGH", "CRITICAL"})

    def test_rolling_count(self):
        r = self.engine().build(dashboard(["0", "0.01", "-0.02"]))
        self.assertEqual(3, r["rolling_point_count"])

    def test_rolling_hash(self):
        r = self.engine().build(dashboard())
        self.assertEqual(64, len(r["rolling_drawdown"][0]["rolling_point_sha256"]))

    def test_analytics_hash(self):
        r = self.engine().build(dashboard())
        self.assertEqual(64, len(r["analytics"]["analytics_sha256"]))

    def test_report_hash(self):
        r = self.engine().build(dashboard())
        self.assertEqual(64, len(r["risk_report_sha256"]))

    def test_deterministic(self):
        a = self.engine().build(dashboard())
        b = self.engine().build(dashboard())
        self.assertEqual(a["risk_report_sha256"], b["risk_report_sha256"])

    def test_bad_status(self):
        x = dashboard()
        x["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "status must be PASS"):
            self.engine().build(x)

    def test_network_rejected(self):
        x = dashboard()
        x["network_used"] = True
        with self.assertRaisesRegex(ValueError, "network_used must be false"):
            self.engine().build(x)

    def test_empty_chart(self):
        x = dashboard()
        x["chart"] = []
        with self.assertRaisesRegex(ValueError, "non-empty list"):
            self.engine().build(x)

    def test_bad_dashboard_hash(self):
        x = dashboard()
        x["dashboard_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "64 characters"):
            self.engine().build(x)

    def test_bad_risk_free_low(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            self.engine().build(dashboard(), risk_free_rate=Decimal("-0.1"))

    def test_bad_risk_free_high(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            self.engine().build(dashboard(), risk_free_rate=Decimal("1.1"))

    def test_bad_var_confidence_low(self):
        with self.assertRaisesRegex(ValueError, "between 0.50 and 1"):
            self.engine().build(dashboard(), var_confidence=Decimal("0.49"))

    def test_bad_var_confidence_high(self):
        with self.assertRaisesRegex(ValueError, "between 0.50 and 1"):
            self.engine().build(dashboard(), var_confidence=Decimal("1"))

    def test_quantile(self):
        q = historical_quantile(
            [Decimal("-0.03"), Decimal("-0.01"), Decimal("0.02")],
            Decimal("0.95"),
        )
        self.assertEqual(Decimal("-0.03"), q)

    def test_sha(self):
        self.assertEqual(64, len(sha256_hex({"x": 1})))


if __name__ == "__main__":
    unittest.main()
