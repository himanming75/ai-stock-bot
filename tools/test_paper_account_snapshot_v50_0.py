import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.paper_account_snapshot_v50_0 import (
    PaperAccountSnapshotBuilder,
    ReconciliationInput,
    canonical_hash,
    load_reconciliation,
)


def make_position(
    *,
    symbol="AAPL",
    quantity="50",
    average_cost="200.0600",
    market_price="205.0000",
    market_value="10250.0000",
    cost_basis="10003.0000",
    unrealized_pnl="247.0000",
    realized_pnl="0.0000",
    total_commission="1.0000",
):
    core = {
        "symbol": symbol,
        "quantity": quantity,
        "average_cost": average_cost,
        "market_price": market_price,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "total_commission": total_commission,
    }
    return {**core, "position_sha256": canonical_hash(core)}


def make_reconciliation(positions=None, **updates):
    positions = positions or [make_position()]
    total_mv = sum(float(x["market_value"]) for x in positions)
    core = {
        "schema_version": "v49.0.paper_portfolio_reconciliation.1",
        "version": "49.0",
        "status": "PASS",
        "decision": "reconcile",
        "simulation_sha256": "s" * 64,
        "starting_cash": "100000.0000",
        "ending_cash": "89997.0000",
        "total_market_value": str(total_mv),
        "total_cost_basis": "10003.0000",
        "total_realized_pnl": "0.0000",
        "total_unrealized_pnl": "247.0000",
        "total_commission": "1.0000",
        "total_equity": str(89997 + total_mv),
        "position_count": len(positions),
        "positions": positions,
        "ledger": [],
        "rejection_reasons": [],
        "network_used": False,
    }
    core.update(updates)
    return ReconciliationInput(
        **core,
        reconciliation_sha256=canonical_hash(core),
    )


class PaperAccountSnapshotV500Tests(unittest.TestCase):
    def builder(self, **kwargs):
        return PaperAccountSnapshotBuilder(mode="paper", **kwargs)

    def build_default(self, **kwargs):
        params = {
            "snapshot_time": "2026-07-29T21:00:00Z",
            "prior_net_liquidation_value": "100100",
            "initial_equity": "100000",
        }
        params.update(kwargs)
        return self.builder().build(make_reconciliation(), **params)

    def test_status_pass(self):
        self.assertEqual("PASS", self.build_default().status)

    def test_decision_snapshot(self):
        self.assertEqual("snapshot", self.build_default().decision)

    def test_cash_balance(self):
        self.assertEqual("89997.0000", self.build_default().cash_balance)

    def test_nlv(self):
        self.assertEqual("100247.0000", self.build_default().net_liquidation_value)

    def test_daily_pnl(self):
        self.assertEqual("147.0000", self.build_default().daily_pnl)

    def test_daily_return(self):
        self.assertEqual("0.001469", self.build_default().daily_return)

    def test_cumulative_pnl(self):
        self.assertEqual("247.0000", self.build_default().cumulative_pnl)

    def test_cumulative_return(self):
        self.assertEqual("0.002470", self.build_default().cumulative_return)

    def test_cash_allocation(self):
        self.assertEqual("0.897753", self.build_default().cash_allocation)

    def test_invested_allocation(self):
        self.assertEqual("0.102247", self.build_default().invested_allocation)

    def test_gross_exposure(self):
        self.assertEqual("0.102247", self.build_default().gross_exposure)

    def test_net_exposure(self):
        self.assertEqual("0.102247", self.build_default().net_exposure)

    def test_long_market_value(self):
        self.assertEqual("10250.0000", self.build_default().long_market_value)

    def test_short_market_value_zero(self):
        self.assertEqual("0.0000", self.build_default().short_market_value)

    def test_buying_power_default(self):
        self.assertEqual("89997.0000", self.build_default().buying_power)

    def test_buying_power_multiplier(self):
        result = self.builder(buying_power_multiplier="2").build(
            make_reconciliation(),
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100100",
            initial_equity="100000",
        )
        self.assertEqual("179994.0000", result.buying_power)

    def test_position_allocation_hash(self):
        result = self.build_default()
        self.assertEqual(64, len(result.positions[0]["allocation_sha256"]))

    def test_snapshot_hash(self):
        self.assertEqual(64, len(self.build_default().snapshot_sha256))

    def test_ledger_created(self):
        result = self.build_default()
        self.assertEqual(1, len(result.ledger))
        self.assertEqual("GENESIS", result.ledger[0]["previous_entry_sha256"])

    def test_network_false(self):
        self.assertFalse(self.build_default().network_used)

    def test_deterministic_hash(self):
        first = self.build_default()
        second = self.build_default()
        self.assertEqual(first.snapshot_sha256, second.snapshot_sha256)

    def test_short_position_exposure(self):
        short = make_position(
            symbol="TSLA",
            quantity="-10",
            average_cost="250",
            market_price="240",
            market_value="-2400",
            cost_basis="-2500",
            unrealized_pnl="100",
        )
        rec = make_reconciliation(
            [short],
            ending_cash="102400",
            total_market_value="-2400",
            total_equity="100000",
        )
        result = self.builder().build(
            rec,
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertEqual("2400.0000", result.short_market_value)
        self.assertEqual("0.024000", result.gross_exposure)
        self.assertEqual("-0.024000", result.net_exposure)

    def test_multiple_positions(self):
        aapl = make_position()
        msft = make_position(
            symbol="MSFT",
            quantity="10",
            average_cost="400",
            market_price="410",
            market_value="4100",
            cost_basis="4000",
            unrealized_pnl="100",
        )
        rec = make_reconciliation(
            [aapl, msft],
            ending_cash="85897",
            total_market_value="14350",
            total_equity="100247",
            position_count=2,
        )
        result = self.builder().build(
            rec,
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertEqual(2, result.position_count)

    def test_status_rejected(self):
        result = self.builder().build(
            make_reconciliation(status="FAIL"),
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertEqual("FAIL", result.status)

    def test_decision_rejected(self):
        result = self.builder().build(
            make_reconciliation(decision="reject"),
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertEqual("FAIL", result.status)

    def test_network_rejected(self):
        result = self.builder().build(
            make_reconciliation(network_used=True),
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertEqual("FAIL", result.status)

    def test_rejection_reasons_rejected(self):
        result = self.builder().build(
            make_reconciliation(rejection_reasons=["bad"]),
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertEqual("FAIL", result.status)

    def test_position_count_mismatch(self):
        result = self.builder().build(
            make_reconciliation(position_count=2),
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertEqual("FAIL", result.status)

    def test_reconciliation_hash_tamper(self):
        rec = make_reconciliation()
        tampered = ReconciliationInput(**{**asdict(rec), "status": "FAIL"})
        result = self.builder().build(
            tampered,
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertIn(
            "V49 reconciliation SHA-256 verification failed.",
            result.rejection_reasons,
        )

    def test_position_hash_tamper(self):
        position = make_position()
        position["market_value"] = "1"
        result = self.builder().build(
            make_reconciliation([position]),
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertEqual("FAIL", result.status)

    def test_equity_mismatch(self):
        result = self.builder().build(
            make_reconciliation(total_equity="1"),
            snapshot_time="2026-07-29T21:00:00Z",
            prior_net_liquidation_value="100000",
            initial_equity="100000",
        )
        self.assertEqual("FAIL", result.status)

    def test_nonpositive_prior_nlv(self):
        result = self.build_default(prior_net_liquidation_value="0")
        self.assertEqual("FAIL", result.status)

    def test_nonpositive_initial_equity(self):
        result = self.build_default(initial_equity="0")
        self.assertEqual("FAIL", result.status)

    def test_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            self.builder().build(
                make_reconciliation(),
                snapshot_time="bad",
                prior_net_liquidation_value="100000",
                initial_equity="100000",
            )

    def test_timestamp_requires_timezone(self):
        with self.assertRaises(ValueError):
            self.builder().build(
                make_reconciliation(),
                snapshot_time="2026-07-29T21:00:00",
                prior_net_liquidation_value="100000",
                initial_equity="100000",
            )

    def test_negative_buying_power_multiplier(self):
        with self.assertRaises(ValueError):
            self.builder(buying_power_multiplier="-1")

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            PaperAccountSnapshotBuilder(mode="bad")

    def test_live_gate(self):
        builder = PaperAccountSnapshotBuilder(mode="live")
        with self.assertRaises(PermissionError):
            builder.build(
                make_reconciliation(),
                snapshot_time="2026-07-29T21:00:00Z",
                prior_net_liquidation_value="100000",
                initial_equity="100000",
            )

    def test_live_not_implemented(self):
        builder = PaperAccountSnapshotBuilder(
            mode="live",
            enable_live=True,
        )
        with self.assertRaises(NotImplementedError):
            builder.build(
                make_reconciliation(),
                snapshot_time="2026-07-29T21:00:00Z",
                prior_net_liquidation_value="100000",
                initial_equity="100000",
            )

    def test_export(self):
        builder = self.builder()
        result = self.build_default()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            builder.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])
            self.assertFalse(payload["network_used"])

    def test_load_reconciliation_export_shape(self):
        rec = make_reconciliation()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rec.json"
            path.write_text(
                json.dumps({"result": asdict(rec)}),
                encoding="utf-8",
            )
            loaded = load_reconciliation(path)
            self.assertEqual(rec, loaded)


if __name__ == "__main__":
    unittest.main()
