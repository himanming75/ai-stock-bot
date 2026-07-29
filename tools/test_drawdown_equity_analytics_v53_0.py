import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.drawdown_equity_analytics_v53_0 import (
    DrawdownEquityAnalyticsEngine,
    SnapshotInput,
    canonical_hash,
    load_snapshot,
)


def make_snapshot(
    *,
    snapshot_time="2026-07-29T21:00:00Z",
    nlv="100000.0000",
    prior_nlv="99000.0000",
    status="PASS",
    decision="snapshot",
    network_used=False,
    rejection_reasons=None,
    positions=None,
):
    positions = positions or []
    rejection_reasons = rejection_reasons or []
    core = {
        "schema_version": "v50.0.paper_account_snapshot.1",
        "version": "50.0",
        "status": status,
        "decision": decision,
        "snapshot_time": snapshot_time,
        "reconciliation_sha256": "r" * 64,
        "cash_balance": "90000.0000",
        "buying_power": "90000.0000",
        "total_market_value": "10000.0000",
        "net_liquidation_value": nlv,
        "prior_net_liquidation_value": prior_nlv,
        "daily_pnl": "1000.0000",
        "daily_return": "0.010101",
        "cumulative_pnl": "1000.0000",
        "cumulative_return": "0.010101",
        "cash_allocation": "0.900000",
        "invested_allocation": "0.100000",
        "gross_exposure": "0.100000",
        "net_exposure": "0.100000",
        "leverage_ratio": "0.100000",
        "long_market_value": "10000.0000",
        "short_market_value": "0.0000",
        "position_count": len(positions),
        "positions": positions,
        "ledger": [],
        "rejection_reasons": rejection_reasons,
        "network_used": network_used,
    }
    return SnapshotInput(**core, snapshot_sha256=canonical_hash(core))


def series(values):
    out = []
    for i, value in enumerate(values):
        out.append(make_snapshot(
            snapshot_time=f"2026-07-{29+i:02d}T21:00:00Z",
            nlv=str(value),
            prior_nlv=str(values[i-1] if i else value),
        ))
    return out


class DrawdownEquityAnalyticsV530Tests(unittest.TestCase):
    def engine(self):
        return DrawdownEquityAnalyticsEngine(mode="paper")

    def test_single_pass(self):
        self.assertEqual("PASS", self.engine().calculate([make_snapshot()]).status)

    def test_decision(self):
        self.assertEqual("drawdown_analytics", self.engine().calculate([make_snapshot()]).decision)

    def test_snapshot_count(self):
        self.assertEqual(1, self.engine().calculate([make_snapshot()]).snapshot_count)

    def test_starting_equity(self):
        self.assertEqual("100000.0000", self.engine().calculate([make_snapshot()]).starting_equity)

    def test_ending_equity(self):
        self.assertEqual("100000.0000", self.engine().calculate([make_snapshot()]).ending_equity)

    def test_highest_equity(self):
        self.assertEqual("110000.0000", self.engine().calculate(series([100000,110000,105000])).highest_equity)

    def test_lowest_equity(self):
        self.assertEqual("90000.0000", self.engine().calculate(series([100000,90000,95000])).lowest_equity)

    def test_equity_change(self):
        self.assertEqual("5000.0000", self.engine().calculate(series([100000,105000])).equity_change)

    def test_total_return(self):
        self.assertEqual("0.050000", self.engine().calculate(series([100000,105000])).total_return)

    def test_positive_periods(self):
        self.assertEqual(2, self.engine().calculate(series([100000,101000,102000])).positive_equity_periods)

    def test_negative_periods(self):
        self.assertEqual(2, self.engine().calculate(series([100000,99000,98000])).negative_equity_periods)

    def test_flat_periods(self):
        self.assertEqual(2, self.engine().calculate(series([100000,100000,100000])).flat_equity_periods)

    def test_drawdown_amount(self):
        self.assertEqual("10000.0000", self.engine().calculate(series([100000,110000,100000])).maximum_drawdown_amount)

    def test_drawdown_rate(self):
        self.assertEqual("0.090909", self.engine().calculate(series([100000,110000,100000])).maximum_drawdown)

    def test_underwater_now(self):
        self.assertTrue(self.engine().calculate(series([100000,110000,100000])).underwater_now)

    def test_current_drawdown_duration(self):
        self.assertEqual(1, self.engine().calculate(series([100000,110000,100000])).current_drawdown_duration_periods)

    def test_recovered_event(self):
        result = self.engine().calculate(series([100000,110000,100000,111000]))
        self.assertEqual(1, result.recovered_drawdown_events)

    def test_unrecovered_event(self):
        result = self.engine().calculate(series([100000,110000,100000]))
        self.assertEqual(1, result.unrecovered_drawdown_events)

    def test_drawdown_event_count(self):
        result = self.engine().calculate(series([100000,110000,100000,111000,105000]))
        self.assertEqual(2, result.drawdown_event_count)

    def test_longest_duration(self):
        result = self.engine().calculate(series([100000,110000,105000,100000,111000]))
        self.assertEqual(2, result.longest_drawdown_duration_periods)

    def test_peak_time(self):
        result = self.engine().calculate(series([100000,110000,100000]))
        self.assertEqual("2026-07-30T21:00:00Z", result.maximum_drawdown_peak_time)

    def test_trough_time(self):
        result = self.engine().calculate(series([100000,110000,100000]))
        self.assertEqual("2026-07-31T21:00:00Z", result.maximum_drawdown_trough_time)

    def test_curve_hash(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(64, len(result.equity_curve[0]["point_sha256"]))

    def test_event_hash(self):
        result = self.engine().calculate(series([100000,110000,100000]))
        self.assertEqual(64, len(result.drawdown_events[0]["event_sha256"]))

    def test_analytics_hash(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(64, len(result.analytics_sha256))

    def test_ledger(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("GENESIS", result.ledger[0]["previous_entry_sha256"])

    def test_deterministic(self):
        a = self.engine().calculate(series([100000,110000,100000]))
        b = self.engine().calculate(series([100000,110000,100000]))
        self.assertEqual(a.analytics_sha256, b.analytics_sha256)

    def test_network_false(self):
        self.assertFalse(self.engine().calculate([make_snapshot()]).network_used)

    def test_empty_fail(self):
        self.assertEqual("FAIL", self.engine().calculate([]).status)

    def test_duplicate_fail(self):
        self.assertEqual("FAIL", self.engine().calculate([make_snapshot(), make_snapshot()]).status)

    def test_status_fail(self):
        self.assertEqual("FAIL", self.engine().calculate([make_snapshot(status="FAIL")]).status)

    def test_decision_fail(self):
        self.assertEqual("FAIL", self.engine().calculate([make_snapshot(decision="reject")]).status)

    def test_network_input_fail(self):
        self.assertEqual("FAIL", self.engine().calculate([make_snapshot(network_used=True)]).status)

    def test_rejection_fail(self):
        self.assertEqual("FAIL", self.engine().calculate([make_snapshot(rejection_reasons=["bad"])]).status)

    def test_position_count_fail(self):
        s = make_snapshot()
        t = SnapshotInput(**{**asdict(s), "position_count": 1})
        self.assertEqual("FAIL", self.engine().calculate([t]).status)

    def test_hash_tamper_fail(self):
        s = make_snapshot()
        t = SnapshotInput(**{**asdict(s), "daily_pnl": "999"})
        self.assertEqual("FAIL", self.engine().calculate([t]).status)

    def test_nonpositive_equity_fail(self):
        self.assertEqual("FAIL", self.engine().calculate([make_snapshot(nlv="0")]).status)

    def test_sorting(self):
        late = make_snapshot(snapshot_time="2026-07-30T21:00:00Z")
        early = make_snapshot(snapshot_time="2026-07-29T21:00:00Z")
        r = self.engine().calculate([late, early])
        self.assertEqual("2026-07-29T21:00:00Z", r.equity_curve[0]["snapshot_time"])

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            DrawdownEquityAnalyticsEngine(mode="bad")

    def test_live_gate(self):
        with self.assertRaises(PermissionError):
            DrawdownEquityAnalyticsEngine(mode="live").calculate([make_snapshot()])

    def test_live_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            DrawdownEquityAnalyticsEngine(mode="live", enable_live=True).calculate([make_snapshot()])

    def test_export(self):
        engine = self.engine()
        result = engine.calculate([make_snapshot()])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            engine.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])

    def test_load_snapshot(self):
        s = make_snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snap.json"
            path.write_text(json.dumps({"result": asdict(s)}), encoding="utf-8")
            self.assertEqual(s, load_snapshot(path))

    def test_recovery_sequence(self):
        r = self.engine().calculate(series([100000,110000,100000,111000]))
        self.assertEqual(4, r.drawdown_events[0]["recovery_sequence"])

    def test_recovery_duration(self):
        r = self.engine().calculate(series([100000,110000,100000,111000]))
        self.assertEqual(2, r.drawdown_events[0]["recovery_duration_periods"])

    def test_trough_sequence(self):
        r = self.engine().calculate(series([100000,110000,100000,105000]))
        self.assertEqual(3, r.drawdown_events[0]["trough_sequence"])


if __name__ == "__main__":
    unittest.main()
