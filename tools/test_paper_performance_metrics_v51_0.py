import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.paper_performance_metrics_v51_0 import (
    PaperPerformanceMetricsEngine,
    SnapshotInput,
    canonical_hash,
    load_snapshot,
    parse_trade_pnls,
)


def make_snapshot(
    *,
    snapshot_time="2026-07-29T21:00:00Z",
    nlv="100247.0000",
    prior_nlv="100100.0000",
    daily_pnl="147.0000",
    cumulative_pnl="247.0000",
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
        "cash_balance": "89997.0000",
        "buying_power": "89997.0000",
        "total_market_value": "10250.0000",
        "net_liquidation_value": nlv,
        "prior_net_liquidation_value": prior_nlv,
        "daily_pnl": daily_pnl,
        "daily_return": "0.001469",
        "cumulative_pnl": cumulative_pnl,
        "cumulative_return": "0.002470",
        "cash_allocation": "0.897753",
        "invested_allocation": "0.102247",
        "gross_exposure": "0.102247",
        "net_exposure": "0.102247",
        "leverage_ratio": "0.102247",
        "long_market_value": "10250.0000",
        "short_market_value": "0.0000",
        "position_count": len(positions),
        "positions": positions,
        "ledger": [],
        "rejection_reasons": rejection_reasons,
        "network_used": network_used,
    }
    return SnapshotInput(
        **core,
        snapshot_sha256=canonical_hash(core),
    )


class PaperPerformanceMetricsV510Tests(unittest.TestCase):
    def engine(self, **kwargs):
        return PaperPerformanceMetricsEngine(mode="paper", **kwargs)

    def test_single_snapshot_pass(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("PASS", result.status)

    def test_decision_metrics(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("metrics", result.decision)

    def test_snapshot_count(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(1, result.snapshot_count)

    def test_trade_count_defaults_to_daily_pnl(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(1, result.trade_count)

    def test_starting_equity_from_prior(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("100100.0000", result.starting_equity)

    def test_ending_equity(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("100247.0000", result.ending_equity)

    def test_total_return(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("147.0000", result.total_return)

    def test_cumulative_return(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("0.001469", result.cumulative_return)

    def test_initial_equity_override(self):
        result = self.engine().calculate(
            [make_snapshot()],
            initial_equity="100000",
        )
        self.assertEqual("247.0000", result.total_return)

    def test_single_win(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["247"],
        )
        self.assertEqual(1, result.winning_trades)
        self.assertEqual("247.0000", result.gross_profit)

    def test_single_loss(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["-50"],
        )
        self.assertEqual(1, result.losing_trades)
        self.assertEqual("50.0000", result.gross_loss)

    def test_breakeven(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["0"],
        )
        self.assertEqual(1, result.breakeven_trades)

    def test_mixed_trade_counts(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "0", "25"],
        )
        self.assertEqual(2, result.winning_trades)
        self.assertEqual(1, result.losing_trades)
        self.assertEqual(1, result.breakeven_trades)

    def test_win_rate(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "0", "25"],
        )
        self.assertEqual("0.500000", result.win_rate)

    def test_loss_rate(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "0", "25"],
        )
        self.assertEqual("0.250000", result.loss_rate)

    def test_breakeven_rate(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "0", "25"],
        )
        self.assertEqual("0.250000", result.breakeven_rate)

    def test_average_win(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "25"],
        )
        self.assertEqual("62.5000", result.average_win)

    def test_average_loss(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "25"],
        )
        self.assertEqual("40.0000", result.average_loss)

    def test_payoff_ratio(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "25"],
        )
        self.assertEqual("1.562500", result.payoff_ratio)

    def test_profit_factor(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "25"],
        )
        self.assertEqual("3.125000", result.profit_factor)

    def test_profit_factor_infinity(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "25"],
        )
        self.assertEqual("Infinity", result.profit_factor)
        self.assertTrue(result.profit_factor_infinite)

    def test_profit_factor_zero(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["-10", "-20"],
        )
        self.assertEqual("0.000000", result.profit_factor)

    def test_expectancy(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "25"],
        )
        self.assertEqual("28.3333", result.expectancy)

    def test_net_profit(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100", "-40", "25"],
        )
        self.assertEqual("85.0000", result.net_profit)

    def test_equity_curve_ordering(self):
        s1 = make_snapshot(
            snapshot_time="2026-07-30T21:00:00Z",
            nlv="101000",
            prior_nlv="100000",
            daily_pnl="1000",
        )
        s0 = make_snapshot(
            snapshot_time="2026-07-29T21:00:00Z",
            nlv="100000",
            prior_nlv="99000",
            daily_pnl="1000",
        )
        result = self.engine().calculate([s1, s0])
        self.assertEqual(
            "2026-07-29T21:00:00Z",
            result.equity_curve[0]["snapshot_time"],
        )

    def test_peak_equity(self):
        snapshots = [
            make_snapshot(
                snapshot_time="2026-07-29T21:00:00Z",
                nlv="100000",
            ),
            make_snapshot(
                snapshot_time="2026-07-30T21:00:00Z",
                nlv="110000",
            ),
            make_snapshot(
                snapshot_time="2026-07-31T21:00:00Z",
                nlv="105000",
            ),
        ]
        result = self.engine().calculate(snapshots)
        self.assertEqual("110000.0000", result.peak_equity)

    def test_lowest_equity(self):
        snapshots = [
            make_snapshot(snapshot_time="2026-07-29T21:00:00Z", nlv="100000"),
            make_snapshot(snapshot_time="2026-07-30T21:00:00Z", nlv="90000"),
        ]
        result = self.engine().calculate(snapshots)
        self.assertEqual("90000.0000", result.lowest_equity)

    def test_max_drawdown_amount(self):
        snapshots = [
            make_snapshot(snapshot_time="2026-07-29T21:00:00Z", nlv="100000"),
            make_snapshot(snapshot_time="2026-07-30T21:00:00Z", nlv="110000"),
            make_snapshot(snapshot_time="2026-07-31T21:00:00Z", nlv="99000"),
        ]
        result = self.engine().calculate(snapshots)
        self.assertEqual("11000.0000", result.maximum_drawdown_amount)

    def test_max_drawdown_rate(self):
        snapshots = [
            make_snapshot(snapshot_time="2026-07-29T21:00:00Z", nlv="100000"),
            make_snapshot(snapshot_time="2026-07-30T21:00:00Z", nlv="110000"),
            make_snapshot(snapshot_time="2026-07-31T21:00:00Z", nlv="99000"),
        ]
        result = self.engine().calculate(snapshots)
        self.assertEqual("0.100000", result.maximum_drawdown)

    def test_current_drawdown(self):
        snapshots = [
            make_snapshot(snapshot_time="2026-07-29T21:00:00Z", nlv="100000"),
            make_snapshot(snapshot_time="2026-07-30T21:00:00Z", nlv="110000"),
            make_snapshot(snapshot_time="2026-07-31T21:00:00Z", nlv="105000"),
        ]
        result = self.engine().calculate(snapshots)
        self.assertEqual("0.045455", result.current_drawdown)

    def test_recovery_factor(self):
        snapshots = [
            make_snapshot(snapshot_time="2026-07-29T21:00:00Z", nlv="100000"),
            make_snapshot(snapshot_time="2026-07-30T21:00:00Z", nlv="110000"),
            make_snapshot(snapshot_time="2026-07-31T21:00:00Z", nlv="105000"),
        ]
        result = self.engine().calculate(
            snapshots,
            trade_pnls=["5000"],
        )
        self.assertEqual("1.000000", result.recovery_factor)

    def test_recovery_factor_infinity(self):
        result = self.engine().calculate(
            [make_snapshot()],
            trade_pnls=["100"],
        )
        self.assertEqual("Infinity", result.recovery_factor)
        self.assertTrue(result.recovery_factor_infinite)

    def test_equity_point_hash(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(64, len(result.equity_curve[0]["point_sha256"]))

    def test_metrics_hash(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(64, len(result.metrics_sha256))

    def test_ledger_created(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(1, len(result.ledger))
        self.assertEqual("GENESIS", result.ledger[0]["previous_entry_sha256"])

    def test_deterministic(self):
        first = self.engine().calculate([make_snapshot()])
        second = self.engine().calculate([make_snapshot()])
        self.assertEqual(first.metrics_sha256, second.metrics_sha256)

    def test_network_false(self):
        self.assertFalse(
            self.engine().calculate([make_snapshot()]).network_used
        )

    def test_empty_snapshots_fail(self):
        result = self.engine().calculate([])
        self.assertEqual("FAIL", result.status)

    def test_snapshot_status_fail(self):
        result = self.engine().calculate([make_snapshot(status="FAIL")])
        self.assertEqual("FAIL", result.status)

    def test_snapshot_decision_fail(self):
        result = self.engine().calculate([make_snapshot(decision="reject")])
        self.assertEqual("FAIL", result.status)

    def test_snapshot_network_fail(self):
        result = self.engine().calculate(
            [make_snapshot(network_used=True)]
        )
        self.assertEqual("FAIL", result.status)

    def test_snapshot_rejection_reasons_fail(self):
        result = self.engine().calculate(
            [make_snapshot(rejection_reasons=["bad"])]
        )
        self.assertEqual("FAIL", result.status)

    def test_position_count_mismatch_fail(self):
        snapshot = make_snapshot()
        tampered = SnapshotInput(
            **{**asdict(snapshot), "position_count": 1}
        )
        result = self.engine().calculate([tampered])
        self.assertEqual("FAIL", result.status)

    def test_snapshot_hash_tamper_fail(self):
        snapshot = make_snapshot()
        tampered = SnapshotInput(
            **{**asdict(snapshot), "daily_pnl": "999"}
        )
        result = self.engine().calculate([tampered])
        self.assertEqual("FAIL", result.status)

    def test_duplicate_time_fail(self):
        result = self.engine().calculate(
            [make_snapshot(), make_snapshot()]
        )
        self.assertEqual("FAIL", result.status)

    def test_nonpositive_equity_fail(self):
        result = self.engine().calculate(
            [make_snapshot(nlv="0")]
        )
        self.assertEqual("FAIL", result.status)

    def test_nonpositive_initial_equity_fail(self):
        result = self.engine().calculate(
            [make_snapshot()],
            initial_equity="0",
        )
        self.assertEqual("FAIL", result.status)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            PaperPerformanceMetricsEngine(mode="bad")

    def test_live_gate(self):
        engine = PaperPerformanceMetricsEngine(mode="live")
        with self.assertRaises(PermissionError):
            engine.calculate([make_snapshot()])

    def test_live_not_implemented(self):
        engine = PaperPerformanceMetricsEngine(
            mode="live",
            enable_live=True,
        )
        with self.assertRaises(NotImplementedError):
            engine.calculate([make_snapshot()])

    def test_parse_trade_pnls(self):
        self.assertEqual(
            ["100", "-50", "25"],
            parse_trade_pnls(["100,-50", "25"]),
        )

    def test_parse_trade_pnls_invalid(self):
        with self.assertRaises(ValueError):
            parse_trade_pnls(["bad"])

    def test_export(self):
        engine = self.engine()
        result = engine.calculate([make_snapshot()])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.json"
            engine.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])
            self.assertFalse(payload["network_used"])

    def test_load_snapshot_export_shape(self):
        snapshot = make_snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text(
                json.dumps({"result": asdict(snapshot)}),
                encoding="utf-8",
            )
            loaded = load_snapshot(path)
            self.assertEqual(snapshot, loaded)


if __name__ == "__main__":
    unittest.main()
