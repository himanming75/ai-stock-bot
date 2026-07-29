import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.paper_portfolio_reconciliation_v49_0 import (
    FillSimulationInput,
    PaperPortfolioReconciler,
    canonical_hash,
    load_simulation,
    parse_market_prices,
)


def make_fill(
    *,
    fill_id="fill-1",
    broker_order_id="paper-1",
    symbol="AAPL",
    side="buy",
    qty="10",
    price="100",
    commission="1",
):
    gross = str(float(qty) * float(price))
    core = {
        "fill_id": fill_id,
        "broker_order_id": broker_order_id,
        "symbol": symbol,
        "side": side,
        "fill_quantity": qty,
        "fill_price": price,
        "gross_notional": gross,
        "commission": commission,
        "slippage_bps": "2.0000",
        "reference_price": price,
        "event_at": "2026-07-29T19:00:00.000001Z",
        "network_used": False,
    }
    return {**core, "fill_sha256": canonical_hash(core)}


def make_order(
    fills=None,
    *,
    broker_order_id="paper-1",
    child_order_id="child-1",
    symbol="AAPL",
    side="buy",
):
    fills = fills or [make_fill()]
    filled_qty = sum(float(x["fill_quantity"]) for x in fills)
    gross = sum(float(x["gross_notional"]) for x in fills)
    commission = sum(float(x["commission"]) for x in fills)
    avg = gross / filled_qty if filled_qty else None
    core = {
        "broker_order_id": broker_order_id,
        "child_order_id": child_order_id,
        "symbol": symbol,
        "side": side,
        "requested_quantity": str(filled_qty),
        "filled_quantity": str(filled_qty),
        "remaining_quantity": "0",
        "weighted_average_fill_price": str(avg) if avg is not None else None,
        "gross_notional": str(gross),
        "total_commission": str(commission),
        "final_status": "FILLED",
        "fills": fills,
    }
    return {**core, "order_result_sha256": canonical_hash(core)}


def make_simulation(orders=None, **updates):
    orders = orders or [make_order()]
    fill_count = sum(len(x["fills"]) for x in orders)
    total_qty = sum(float(x["filled_quantity"]) for x in orders)
    total_gross = sum(float(x["gross_notional"]) for x in orders)
    total_commission = sum(float(x["total_commission"]) for x in orders)
    core = {
        "schema_version": "v48.0.paper_fill_simulation.1",
        "version": "48.0",
        "status": "PASS",
        "decision": "simulate",
        "gateway_sha256": "g" * 64,
        "order_count": len(orders),
        "fill_event_count": fill_count,
        "fully_filled_count": len(orders),
        "partially_filled_count": 0,
        "unfilled_count": 0,
        "total_filled_quantity": str(total_qty),
        "total_gross_notional": str(total_gross),
        "total_commission": str(total_commission),
        "orders": orders,
        "ledger": [],
        "rejection_reasons": [],
        "network_used": False,
    }
    core.update(updates)
    return FillSimulationInput(**core, simulation_sha256=canonical_hash(core))


class PaperPortfolioReconciliationV490Tests(unittest.TestCase):
    def reconciler(self, **kwargs):
        return PaperPortfolioReconciler(
            mode="paper",
            reference_time="2026-07-29T20:00:00Z",
            **kwargs,
        )

    def test_single_buy_cash(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "110"},
        )
        self.assertEqual("8999.0000", result.ending_cash)

    def test_single_buy_quantity(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "110"},
        )
        self.assertEqual("10", result.positions[0]["quantity"])

    def test_average_cost_includes_commission(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "110"},
        )
        self.assertEqual("100.1000", result.positions[0]["average_cost"])

    def test_market_value(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "110"},
        )
        self.assertEqual("1100.0000", result.total_market_value)

    def test_unrealized_pnl(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "110"},
        )
        self.assertEqual("99.0000", result.total_unrealized_pnl)

    def test_total_equity(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "110"},
        )
        self.assertEqual("10099.0000", result.total_equity)

    def test_multiple_buys_weighted_average(self):
        fills = [
            make_fill(fill_id="f1", qty="10", price="100", commission="1"),
            make_fill(fill_id="f2", qty="10", price="120", commission="1"),
        ]
        order = make_order(fills=fills)
        result = self.reconciler().reconcile(
            make_simulation([order]),
            starting_cash="10000",
            market_prices={"AAPL": "130"},
        )
        self.assertEqual("110.1000", result.positions[0]["average_cost"])

    def test_sell_realized_profit(self):
        buy = make_order(
            [make_fill(fill_id="b", side="buy", qty="10", price="100", commission="1")],
            broker_order_id="b1",
            side="buy",
        )
        sell = make_order(
            [make_fill(fill_id="s", broker_order_id="s1", side="sell", qty="5", price="120", commission="1")],
            broker_order_id="s1",
            side="sell",
        )
        result = self.reconciler().reconcile(
            make_simulation([buy, sell]),
            starting_cash="10000",
            market_prices={"AAPL": "125"},
        )
        self.assertEqual("98.5000", result.total_realized_pnl)

    def test_sell_remaining_quantity(self):
        buy = make_order(
            [make_fill(fill_id="b", side="buy", qty="10", price="100", commission="1")],
            broker_order_id="b1",
            side="buy",
        )
        sell = make_order(
            [make_fill(fill_id="s", broker_order_id="s1", side="sell", qty="5", price="120", commission="1")],
            broker_order_id="s1",
            side="sell",
        )
        result = self.reconciler().reconcile(
            make_simulation([buy, sell]),
            starting_cash="10000",
            market_prices={"AAPL": "125"},
        )
        self.assertEqual("5", result.positions[0]["quantity"])

    def test_full_close_average_cost_zero(self):
        buy = make_order(
            [make_fill(fill_id="b", side="buy", qty="10", price="100", commission="1")],
            broker_order_id="b1",
            side="buy",
        )
        sell = make_order(
            [make_fill(fill_id="s", broker_order_id="s1", side="sell", qty="10", price="120", commission="1")],
            broker_order_id="s1",
            side="sell",
        )
        result = self.reconciler().reconcile(
            make_simulation([buy, sell]),
            starting_cash="10000",
            market_prices={"AAPL": "125"},
        )
        self.assertEqual("0.0000", result.positions[0]["average_cost"])

    def test_sell_without_position_rejected(self):
        sell = make_order(
            [make_fill(side="sell")],
            side="sell",
        )
        result = self.reconciler().reconcile(
            make_simulation([sell]),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_short_allowed(self):
        sell = make_order(
            [make_fill(side="sell")],
            side="sell",
        )
        result = self.reconciler(allow_short=True).reconcile(
            make_simulation([sell]),
            starting_cash="10000",
            market_prices={"AAPL": "90"},
        )
        self.assertEqual("-10", result.positions[0]["quantity"])

    def test_short_unrealized_profit(self):
        sell = make_order(
            [make_fill(side="sell", price="100")],
            side="sell",
        )
        result = self.reconciler(allow_short=True).reconcile(
            make_simulation([sell]),
            starting_cash="10000",
            market_prices={"AAPL": "90"},
        )
        self.assertEqual("99.0000", result.total_unrealized_pnl)

    def test_cover_short(self):
        sell = make_order(
            [make_fill(fill_id="s", side="sell", price="100")],
            broker_order_id="s1",
            side="sell",
        )
        buy = make_order(
            [make_fill(fill_id="b", broker_order_id="b1", side="buy", price="90")],
            broker_order_id="b1",
            side="buy",
        )
        result = self.reconciler(allow_short=True).reconcile(
            make_simulation([sell, buy]),
            starting_cash="10000",
            market_prices={"AAPL": "90"},
        )
        self.assertEqual("98.0000", result.total_realized_pnl)

    def test_multiple_symbols(self):
        aapl = make_order(
            [make_fill(symbol="AAPL")],
            symbol="AAPL",
        )
        msft = make_order(
            [make_fill(fill_id="m", broker_order_id="m1", symbol="MSFT", price="200")],
            broker_order_id="m1",
            child_order_id="c2",
            symbol="MSFT",
        )
        result = self.reconciler().reconcile(
            make_simulation([aapl, msft]),
            starting_cash="10000",
            market_prices={"AAPL": "110", "MSFT": "210"},
        )
        self.assertEqual(2, result.position_count)

    def test_missing_market_price_rejected(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"MSFT": "200"},
        )
        self.assertEqual("FAIL", result.status)

    def test_negative_starting_cash_rejected(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="-1",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_nonpositive_market_price_rejected(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "0"},
        )
        self.assertEqual("FAIL", result.status)

    def test_simulation_status_rejected(self):
        result = self.reconciler().reconcile(
            make_simulation(status="FAIL"),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_simulation_decision_rejected(self):
        result = self.reconciler().reconcile(
            make_simulation(decision="reject"),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_simulation_network_rejected(self):
        result = self.reconciler().reconcile(
            make_simulation(network_used=True),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_simulation_rejection_reasons_rejected(self):
        result = self.reconciler().reconcile(
            make_simulation(rejection_reasons=["bad"]),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_simulation_count_mismatch(self):
        result = self.reconciler().reconcile(
            make_simulation(order_count=2),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_simulation_hash_tamper(self):
        sim = make_simulation()
        tampered = FillSimulationInput(**{**asdict(sim), "status": "FAIL"})
        result = self.reconciler().reconcile(
            tampered,
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertIn(
            "V48 simulation SHA-256 verification failed.",
            result.rejection_reasons,
        )

    def test_order_hash_tamper(self):
        order = make_order()
        order["gross_notional"] = "1"
        result = self.reconciler().reconcile(
            make_simulation([order]),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_fill_hash_tamper(self):
        fill = make_fill()
        fill["fill_price"] = "101"
        order = make_order([fill])
        result = self.reconciler().reconcile(
            make_simulation([order]),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_fill_network_rejected(self):
        fill = make_fill()
        fill["network_used"] = True
        core = {k: v for k, v in fill.items() if k != "fill_sha256"}
        fill["fill_sha256"] = canonical_hash(core)
        order = make_order([fill])
        result = self.reconciler().reconcile(
            make_simulation([order]),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_gross_mismatch_rejected(self):
        fill = make_fill()
        fill["gross_notional"] = "1"
        core = {k: v for k, v in fill.items() if k != "fill_sha256"}
        fill["fill_sha256"] = canonical_hash(core)
        order = make_order([fill])
        result = self.reconciler().reconcile(
            make_simulation([order]),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_order_quantity_mismatch_rejected(self):
        order = make_order()
        order["filled_quantity"] = "11"
        core = {k: v for k, v in order.items() if k != "order_result_sha256"}
        order["order_result_sha256"] = canonical_hash(core)
        result = self.reconciler().reconcile(
            make_simulation([order]),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_order_gross_mismatch_rejected(self):
        order = make_order()
        order["gross_notional"] = "999"
        core = {k: v for k, v in order.items() if k != "order_result_sha256"}
        order["order_result_sha256"] = canonical_hash(core)
        result = self.reconciler().reconcile(
            make_simulation([order]),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_order_commission_mismatch_rejected(self):
        order = make_order()
        order["total_commission"] = "9"
        core = {k: v for k, v in order.items() if k != "order_result_sha256"}
        order["order_result_sha256"] = canonical_hash(core)
        result = self.reconciler().reconcile(
            make_simulation([order]),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("FAIL", result.status)

    def test_position_hash_present(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual(64, len(result.positions[0]["position_sha256"]))

    def test_reconciliation_hash_present(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual(64, len(result.reconciliation_sha256))

    def test_deterministic_hash(self):
        first = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        second = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual(first.reconciliation_sha256, second.reconciliation_sha256)

    def test_ledger_hash_chain(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertEqual("GENESIS", result.ledger[0]["previous_entry_sha256"])
        for left, right in zip(result.ledger, result.ledger[1:]):
            self.assertEqual(
                left["entry_sha256"],
                right["previous_entry_sha256"],
            )

    def test_network_false(self):
        result = self.reconciler().reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        self.assertFalse(result.network_used)

    def test_export(self):
        reconciler = self.reconciler()
        result = reconciler.reconcile(
            make_simulation(),
            starting_cash="10000",
            market_prices={"AAPL": "100"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "portfolio.json"
            reconciler.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])
            self.assertFalse(payload["network_used"])

    def test_load_simulation_export_shape(self):
        sim = make_simulation()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "simulation.json"
            path.write_text(
                json.dumps({"result": asdict(sim)}),
                encoding="utf-8",
            )
            loaded = load_simulation(path)
            self.assertEqual(sim, loaded)

    def test_parse_market_prices(self):
        self.assertEqual(
            {"AAPL": "200", "MSFT": "400"},
            parse_market_prices("AAPL=200,MSFT=400"),
        )

    def test_parse_market_prices_invalid(self):
        with self.assertRaises(ValueError):
            parse_market_prices("AAPL")

    def test_parse_market_prices_empty(self):
        with self.assertRaises(ValueError):
            parse_market_prices("")

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            PaperPortfolioReconciler(mode="bad")

    def test_live_gate(self):
        reconciler = PaperPortfolioReconciler(mode="live")
        with self.assertRaises(PermissionError):
            reconciler.reconcile(
                make_simulation(),
                starting_cash="10000",
                market_prices={"AAPL": "100"},
            )

    def test_live_transport_not_implemented(self):
        reconciler = PaperPortfolioReconciler(
            mode="live",
            enable_live=True,
        )
        with self.assertRaises(NotImplementedError):
            reconciler.reconcile(
                make_simulation(),
                starting_cash="10000",
                market_prices={"AAPL": "100"},
            )


if __name__ == "__main__":
    unittest.main()
