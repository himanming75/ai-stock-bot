import unittest
from decimal import Decimal

from tools.strategy_quality_gate_v65_0 import StrategyQualityGate, sha256_hex


def v64(trades=0, win_rate="0", profit_factor="0", expectancy="0"):
    return {
        "status": "PASS",
        "network_used": False,
        "strategy_report_sha256": "e" * 64,
        "closed_trade_count": trades,
        "overall": {
            "trade_count": trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
        },
    }


def v63(risk_score="0", risk_level="LOW"):
    return {
        "status": "PASS",
        "network_used": False,
        "risk_report_sha256": "f" * 64,
        "analytics": {
            "risk_score": risk_score,
            "risk_level": risk_level,
        },
    }


class TestV65(unittest.TestCase):
    def gate(self):
        return StrategyQualityGate()

    def test_status(self):
        self.assertEqual("PASS", self.gate().evaluate(v64(), v63())["status"])

    def test_version(self):
        self.assertEqual("65.0", self.gate().evaluate(v64(), v63())["version"])

    def test_network_false(self):
        self.assertFalse(self.gate().evaluate(v64(), v63())["network_used"])

    def test_insufficient_data(self):
        r = self.gate().evaluate(v64(trades=0), v63())
        self.assertEqual("INSUFFICIENT_DATA", r["quality_gate"])

    def test_insufficient_not_live(self):
        r = self.gate().evaluate(v64(trades=0), v63())
        self.assertFalse(r["approved_for_live"])

    def test_insufficient_not_extended_paper(self):
        r = self.gate().evaluate(v64(trades=0), v63())
        self.assertFalse(r["approved_for_extended_paper"])

    def test_approve(self):
        r = self.gate().evaluate(
            v64(30, "0.60", "1.80", "12"),
            v63("20", "LOW"),
        )
        self.assertEqual("APPROVE", r["quality_gate"])

    def test_approve_extended_paper(self):
        r = self.gate().evaluate(
            v64(30, "0.60", "1.80", "12"),
            v63("20", "LOW"),
        )
        self.assertTrue(r["approved_for_extended_paper"])

    def test_approve_still_not_live(self):
        r = self.gate().evaluate(
            v64(30, "0.60", "1.80", "12"),
            v63("20", "LOW"),
        )
        self.assertFalse(r["approved_for_live"])

    def test_watch(self):
        r = self.gate().evaluate(
            v64(25, "0.50", "1.20", "1"),
            v63("50", "MODERATE"),
        )
        self.assertEqual("WATCH", r["quality_gate"])

    def test_reject_bad_performance(self):
        r = self.gate().evaluate(
            v64(25, "0.30", "0.60", "-20"),
            v63("30", "MODERATE"),
        )
        self.assertEqual("REJECT", r["quality_gate"])

    def test_reject_high_risk(self):
        r = self.gate().evaluate(
            v64(25, "0.70", "2.00", "20"),
            v63("80", "CRITICAL"),
        )
        self.assertEqual("REJECT", r["quality_gate"])

    def test_minimum_trade_boundary(self):
        r = self.gate().evaluate(
            v64(20, "0.60", "1.80", "12"),
            v63("20", "LOW"),
        )
        self.assertEqual("APPROVE", r["quality_gate"])

    def test_approve_win_rate_boundary(self):
        r = self.gate().evaluate(
            v64(20, "0.55", "1.80", "12"),
            v63("20", "LOW"),
        )
        self.assertEqual("APPROVE", r["quality_gate"])

    def test_approve_profit_factor_boundary(self):
        r = self.gate().evaluate(
            v64(20, "0.60", "1.50", "12"),
            v63("20", "LOW"),
        )
        self.assertEqual("APPROVE", r["quality_gate"])

    def test_approve_expectancy_must_be_positive(self):
        r = self.gate().evaluate(
            v64(20, "0.60", "1.50", "0"),
            v63("20", "LOW"),
        )
        self.assertEqual("WATCH", r["quality_gate"])

    def test_approve_risk_boundary(self):
        r = self.gate().evaluate(
            v64(20, "0.60", "1.50", "10"),
            v63("40", "MODERATE"),
        )
        self.assertEqual("APPROVE", r["quality_gate"])

    def test_reject_risk_boundary(self):
        r = self.gate().evaluate(
            v64(20, "0.60", "1.50", "10"),
            v63("70", "HIGH"),
        )
        self.assertEqual("REJECT", r["quality_gate"])

    def test_observed_values(self):
        r = self.gate().evaluate(v64(25, "0.5", "1.2", "3"), v63("30"))
        self.assertEqual("0.500000", r["observed"]["win_rate"])

    def test_thresholds_present(self):
        r = self.gate().evaluate(v64(), v63())
        self.assertEqual(20, r["thresholds"]["minimum_trades"])

    def test_approve_checks_present(self):
        r = self.gate().evaluate(v64(), v63())
        self.assertIn("win_rate", r["approve_checks"])

    def test_watch_checks_present(self):
        r = self.gate().evaluate(v64(), v63())
        self.assertIn("profit_factor", r["watch_checks"])

    def test_reason_present(self):
        r = self.gate().evaluate(v64(), v63())
        self.assertTrue(r["reasons"])

    def test_hash_length(self):
        r = self.gate().evaluate(v64(), v63())
        self.assertEqual(64, len(r["quality_gate_sha256"]))

    def test_deterministic(self):
        a = self.gate().evaluate(v64(), v63())
        b = self.gate().evaluate(v64(), v63())
        self.assertEqual(a["quality_gate_sha256"], b["quality_gate_sha256"])

    def test_bad_v64_status(self):
        x = v64()
        x["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "v64 status must be PASS"):
            self.gate().evaluate(x, v63())

    def test_bad_v64_network(self):
        x = v64()
        x["network_used"] = True
        with self.assertRaisesRegex(ValueError, "v64 network_used must be false"):
            self.gate().evaluate(x, v63())

    def test_bad_v64_hash(self):
        x = v64()
        x["strategy_report_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "64 characters"):
            self.gate().evaluate(x, v63())

    def test_bad_v63_status(self):
        x = v63()
        x["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "v63 status must be PASS"):
            self.gate().evaluate(v64(), x)

    def test_bad_v63_network(self):
        x = v63()
        x["network_used"] = True
        with self.assertRaisesRegex(ValueError, "v63 network_used must be false"):
            self.gate().evaluate(v64(), x)

    def test_bad_v63_hash(self):
        x = v63()
        x["risk_report_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "64 characters"):
            self.gate().evaluate(v64(), x)

    def test_bad_minimum_trades(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            self.gate().evaluate(v64(), v63(), minimum_trades=0)

    def test_bad_overall(self):
        x = v64()
        x["overall"] = None
        with self.assertRaisesRegex(ValueError, "overall must be an object"):
            self.gate().evaluate(x, v63())

    def test_bad_analytics(self):
        x = v63()
        x["analytics"] = None
        with self.assertRaisesRegex(ValueError, "analytics must be an object"):
            self.gate().evaluate(v64(), x)

    def test_sha(self):
        self.assertEqual(64, len(sha256_hex({"x": 1})))


if __name__ == "__main__":
    unittest.main()
