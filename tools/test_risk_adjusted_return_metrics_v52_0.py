import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.risk_adjusted_return_metrics_v52_0 import (
    RiskAdjustedReturnMetricsEngine,
    SnapshotInput,
    canonical_hash,
    load_snapshot,
    sample_stddev,
)


def make_snapshot(
    *,
    snapshot_time="2026-07-29T21:00:00Z",
    nlv="100100.0000",
    prior_nlv="100000.0000",
    status="PASS",
    decision="snapshot",
    network_used=False,
    rejection_reasons=None,
    positions=None,
):
    positions = positions or []
    rejection_reasons = rejection_reasons or []
    daily_pnl = str(float(nlv) - float(prior_nlv))
    core = {
        "schema_version": "v50.0.paper_account_snapshot.1",
        "version": "50.0",
        "status": status,
        "decision": decision,
        "snapshot_time": snapshot_time,
        "reconciliation_sha256": "r" * 64,
        "cash_balance": "90000.0000",
        "buying_power": "90000.0000",
        "total_market_value": "10100.0000",
        "net_liquidation_value": nlv,
        "prior_net_liquidation_value": prior_nlv,
        "daily_pnl": daily_pnl,
        "daily_return": "0.001000",
        "cumulative_pnl": "100.0000",
        "cumulative_return": "0.001000",
        "cash_allocation": "0.899101",
        "invested_allocation": "0.100899",
        "gross_exposure": "0.100899",
        "net_exposure": "0.100899",
        "leverage_ratio": "0.100899",
        "long_market_value": "10100.0000",
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


class RiskAdjustedReturnMetricsV520Tests(unittest.TestCase):
    def engine(self, **kwargs):
        return RiskAdjustedReturnMetricsEngine(mode="paper", **kwargs)

    def test_single_snapshot_pass(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("PASS", result.status)

    def test_decision(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("risk_metrics", result.decision)

    def test_snapshot_count(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(1, result.snapshot_count)

    def test_period_count(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(1, result.period_count)

    def test_period_return(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("0.001000", result.return_points[0]["period_return"])

    def test_mean_return(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("0.001000", result.arithmetic_mean_return)

    def test_positive_period(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(1, result.positive_periods)

    def test_negative_period(self):
        result = self.engine().calculate([
            make_snapshot(nlv="99000", prior_nlv="100000")
        ])
        self.assertEqual(1, result.negative_periods)

    def test_flat_period(self):
        result = self.engine().calculate([
            make_snapshot(nlv="100000", prior_nlv="100000")
        ])
        self.assertEqual(1, result.flat_periods)

    def test_best_period_return(self):
        result = self.engine().calculate([
            make_snapshot(
                snapshot_time="2026-07-29T21:00:00Z",
                nlv="101000",
                prior_nlv="100000",
            ),
            make_snapshot(
                snapshot_time="2026-07-30T21:00:00Z",
                nlv="103000",
                prior_nlv="101000",
            ),
        ])
        self.assertEqual("0.019802", result.best_period_return)

    def test_worst_period_return(self):
        result = self.engine().calculate([
            make_snapshot(
                snapshot_time="2026-07-29T21:00:00Z",
                nlv="101000",
                prior_nlv="100000",
            ),
            make_snapshot(
                snapshot_time="2026-07-30T21:00:00Z",
                nlv="99000",
                prior_nlv="101000",
            ),
        ])
        self.assertEqual("-0.019802", result.worst_period_return)

    def test_cumulative_return(self):
        result = self.engine().calculate([
            make_snapshot(
                snapshot_time="2026-07-29T21:00:00Z",
                nlv="101000",
                prior_nlv="100000",
            ),
            make_snapshot(
                snapshot_time="2026-07-30T21:00:00Z",
                nlv="103020",
                prior_nlv="101000",
            ),
        ])
        self.assertEqual("0.030200", result.cumulative_return)

    def test_volatility_zero_single_period(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("0.000000", result.volatility_periodic)

    def test_sharpe_infinity_single_positive(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("Infinity", result.sharpe_ratio)
        self.assertTrue(result.sharpe_ratio_infinite)

    def test_sortino_infinity_positive_only(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("Infinity", result.sortino_ratio)
        self.assertTrue(result.sortino_ratio_infinite)

    def test_sharpe_finite(self):
        result = self.engine().calculate([
            make_snapshot(
                snapshot_time="2026-07-29T21:00:00Z",
                nlv="101000",
                prior_nlv="100000",
            ),
            make_snapshot(
                snapshot_time="2026-07-30T21:00:00Z",
                nlv="100000",
                prior_nlv="101000",
            ),
            make_snapshot(
                snapshot_time="2026-07-31T21:00:00Z",
                nlv="102000",
                prior_nlv="100000",
            ),
        ])
        self.assertNotIn("Infinity", result.sharpe_ratio)

    def test_sortino_finite(self):
        result = self.engine().calculate([
            make_snapshot(
                snapshot_time="2026-07-29T21:00:00Z",
                nlv="101000",
                prior_nlv="100000",
            ),
            make_snapshot(
                snapshot_time="2026-07-30T21:00:00Z",
                nlv="99000",
                prior_nlv="101000",
            ),
        ])
        self.assertNotIn("Infinity", result.sortino_ratio)

    def test_annualization_factor(self):
        result = self.engine().calculate(
            [make_snapshot()],
            annualization_factor="365",
        )
        self.assertEqual("365.000000", result.annualization_factor)

    def test_risk_free_rate(self):
        result = self.engine().calculate(
            [make_snapshot()],
            risk_free_rate_annual="0.05",
        )
        self.assertEqual("0.050000", result.risk_free_rate_annual)

    def test_target_return(self):
        result = self.engine().calculate(
            [make_snapshot()],
            target_return_annual="0.03",
        )
        self.assertEqual("0.030000", result.target_return_annual)

    def test_max_drawdown(self):
        result = self.engine().calculate([
            make_snapshot(
                snapshot_time="2026-07-29T21:00:00Z",
                nlv="100000",
                prior_nlv="99000",
            ),
            make_snapshot(
                snapshot_time="2026-07-30T21:00:00Z",
                nlv="110000",
                prior_nlv="100000",
            ),
            make_snapshot(
                snapshot_time="2026-07-31T21:00:00Z",
                nlv="99000",
                prior_nlv="110000",
            ),
        ])
        self.assertEqual("0.100000", result.maximum_drawdown)

    def test_calmar_infinity_no_drawdown(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual("Infinity", result.calmar_ratio)

    def test_return_point_hash(self):
        result = self.engine().calculate([make_snapshot()])
        self.assertEqual(64, len(result.return_points[0]["point_sha256"]))

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
        result = self.engine().calculate([make_snapshot()])
        self.assertFalse(result.network_used)

    def test_sorted_by_time(self):
        late = make_snapshot(snapshot_time="2026-07-30T21:00:00Z")
        early = make_snapshot(snapshot_time="2026-07-29T21:00:00Z")
        result = self.engine().calculate([late, early])
        self.assertEqual(
            "2026-07-29T21:00:00Z",
            result.return_points[0]["snapshot_time"],
        )

    def test_empty_fail(self):
        result = self.engine().calculate([])
        self.assertEqual("FAIL", result.status)

    def test_duplicate_time_fail(self):
        result = self.engine().calculate([make_snapshot(), make_snapshot()])
        self.assertEqual("FAIL", result.status)

    def test_status_fail(self):
        result = self.engine().calculate([make_snapshot(status="FAIL")])
        self.assertEqual("FAIL", result.status)

    def test_decision_fail(self):
        result = self.engine().calculate([make_snapshot(decision="reject")])
        self.assertEqual("FAIL", result.status)

    def test_network_input_fail(self):
        result = self.engine().calculate([make_snapshot(network_used=True)])
        self.assertEqual("FAIL", result.status)

    def test_rejection_reasons_fail(self):
        result = self.engine().calculate([
            make_snapshot(rejection_reasons=["bad"])
        ])
        self.assertEqual("FAIL", result.status)

    def test_position_count_mismatch_fail(self):
        snapshot = make_snapshot()
        tampered = SnapshotInput(
            **{**asdict(snapshot), "position_count": 1}
        )
        result = self.engine().calculate([tampered])
        self.assertEqual("FAIL", result.status)

    def test_hash_tamper_fail(self):
        snapshot = make_snapshot()
        tampered = SnapshotInput(
            **{**asdict(snapshot), "daily_pnl": "999"}
        )
        result = self.engine().calculate([tampered])
        self.assertEqual("FAIL", result.status)

    def test_nonpositive_beginning_equity_fail(self):
        result = self.engine().calculate([
            make_snapshot(prior_nlv="0")
        ])
        self.assertEqual("FAIL", result.status)

    def test_nonpositive_ending_equity_fail(self):
        result = self.engine().calculate([
            make_snapshot(nlv="0")
        ])
        self.assertEqual("FAIL", result.status)

    def test_bad_annualization_factor_fail(self):
        result = self.engine().calculate(
            [make_snapshot()],
            annualization_factor="0",
        )
        self.assertEqual("FAIL", result.status)

    def test_bad_risk_free_rate_fail(self):
        result = self.engine().calculate(
            [make_snapshot()],
            risk_free_rate_annual="-1",
        )
        self.assertEqual("FAIL", result.status)

    def test_bad_target_return_fail(self):
        result = self.engine().calculate(
            [make_snapshot()],
            target_return_annual="-1",
        )
        self.assertEqual("FAIL", result.status)

    def test_invalid_numeric_raises(self):
        with self.assertRaises(ValueError):
            self.engine().calculate(
                [make_snapshot()],
                annualization_factor="bad",
            )

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            RiskAdjustedReturnMetricsEngine(mode="bad")

    def test_live_gate(self):
        engine = RiskAdjustedReturnMetricsEngine(mode="live")
        with self.assertRaises(PermissionError):
            engine.calculate([make_snapshot()])

    def test_live_not_implemented(self):
        engine = RiskAdjustedReturnMetricsEngine(
            mode="live",
            enable_live=True,
        )
        with self.assertRaises(NotImplementedError):
            engine.calculate([make_snapshot()])

    def test_export(self):
        engine = self.engine()
        result = engine.calculate([make_snapshot()])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk.json"
            engine.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])
            self.assertFalse(payload["network_used"])

    def test_load_snapshot(self):
        snapshot = make_snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text(
                json.dumps({"result": asdict(snapshot)}),
                encoding="utf-8",
            )
            loaded = load_snapshot(path)
            self.assertEqual(snapshot, loaded)

    def test_sample_stddev_single(self):
        self.assertEqual(0, sample_stddev([1]))

    def test_sample_stddev_two_values(self):
        value = sample_stddev([0, 2])
        self.assertEqual("1.414214", f"{value:.6f}")


if __name__ == "__main__":
    unittest.main()
