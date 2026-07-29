import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.paper_fill_simulator_v48_0 import (
    GatewayInput,
    PaperFillSimulator,
    canonical_hash,
    load_gateway,
)


def make_order(**updates):
    core = {
        "accepted_at": "2026-07-29T18:00:00.000001Z",
        "broker_order_id": "paper-order-1",
        "child_order_id": "v46-child-1",
        "limit_price": None,
        "network_used": False,
        "order_type": "market",
        "parent_client_order_id": "v43-parent-1",
        "quantity": "50",
        "side": "buy",
        "status": "ACCEPTED",
        "symbol": "AAPL",
        "time_in_force": "day",
        "updated_at": "2026-07-29T18:00:00.000001Z",
        "venue": "PAPER_PRIMARY",
    }
    core.update(updates)
    return {**core, "broker_order_sha256": canonical_hash(core)}


def make_gateway(orders=None, **updates):
    orders = orders or [make_order()]
    core = {
        "schema_version": "v47.0.paper_broker_gateway.1",
        "version": "47.0",
        "status": "PASS",
        "decision": "accept",
        "route_sha256": "r" * 64,
        "accepted_count": len(orders),
        "rejected_count": 0,
        "duplicate_count": 0,
        "orders": orders,
        "ledger": [],
        "rejection_reasons": [],
        "network_used": False,
    }
    core.update(updates)
    return GatewayInput(**core, gateway_sha256=canonical_hash(core))


class PaperFillSimulatorV480Tests(unittest.TestCase):
    def simulator(self, **kwargs):
        return PaperFillSimulator(
            mode="paper",
            reference_time="2026-07-29T19:00:00Z",
            **kwargs,
        )

    def test_market_order_full_fill(self):
        result = self.simulator().simulate(
            make_gateway(), reference_price="200", liquidity_slices=["100"]
        )
        self.assertEqual("PASS", result.status)
        self.assertEqual(1, result.fully_filled_count)
        self.assertEqual("50", result.total_filled_quantity)

    def test_market_buy_slippage(self):
        result = self.simulator(slippage_bps="10").simulate(
            make_gateway(), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("100.1000", result.orders[0]["weighted_average_fill_price"])

    def test_market_sell_slippage(self):
        order = make_order(side="sell")
        result = self.simulator(slippage_bps="10").simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("99.9000", result.orders[0]["weighted_average_fill_price"])

    def test_partial_fill(self):
        result = self.simulator().simulate(
            make_gateway(), reference_price="200", liquidity_slices=["20"]
        )
        order = result.orders[0]
        self.assertEqual("PARTIAL_FILL", order["final_status"])
        self.assertEqual("20", order["filled_quantity"])
        self.assertEqual("30", order["remaining_quantity"])

    def test_multiple_slices_full_fill(self):
        result = self.simulator().simulate(
            make_gateway(),
            reference_price="200",
            liquidity_slices=["10", "15", "25"],
        )
        self.assertEqual(3, result.fill_event_count)
        self.assertEqual("FILLED", result.orders[0]["final_status"])

    def test_zero_liquidity(self):
        result = self.simulator().simulate(
            make_gateway(), reference_price="200", liquidity_slices=["0"]
        )
        self.assertEqual(1, result.unfilled_count)
        self.assertEqual("WORKING", result.orders[0]["final_status"])

    def test_empty_liquidity(self):
        result = self.simulator().simulate(
            make_gateway(), reference_price="200", liquidity_slices=[]
        )
        self.assertEqual("WORKING", result.orders[0]["final_status"])

    def test_buy_limit_not_market_crossed(self):
        order = make_order(order_type="limit", limit_price="99")
        result = self.simulator().simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("ACCEPTED", result.orders[0]["final_status"])
        self.assertEqual(0, result.fill_event_count)

    def test_buy_limit_fills(self):
        order = make_order(order_type="limit", limit_price="101")
        result = self.simulator(slippage_bps="20").simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("100.2000", result.orders[0]["weighted_average_fill_price"])

    def test_buy_limit_caps_price(self):
        order = make_order(order_type="limit", limit_price="100.05")
        result = self.simulator(slippage_bps="20").simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("100.0500", result.orders[0]["weighted_average_fill_price"])

    def test_sell_limit_not_crossed(self):
        order = make_order(side="sell", order_type="limit", limit_price="101")
        result = self.simulator().simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("ACCEPTED", result.orders[0]["final_status"])

    def test_sell_limit_fills(self):
        order = make_order(side="sell", order_type="limit", limit_price="99")
        result = self.simulator(slippage_bps="20").simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("99.8000", result.orders[0]["weighted_average_fill_price"])

    def test_minimum_commission(self):
        result = self.simulator(
            commission_per_share="0.005", minimum_commission="1.00"
        ).simulate(
            make_gateway(), reference_price="100", liquidity_slices=["10"]
        )
        self.assertEqual("1.0000", result.orders[0]["total_commission"])

    def test_per_share_commission(self):
        result = self.simulator(
            commission_per_share="0.05", minimum_commission="1.00"
        ).simulate(
            make_gateway(), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("2.5000", result.orders[0]["total_commission"])

    def test_commission_per_fill(self):
        result = self.simulator(
            commission_per_share="0", minimum_commission="1.00"
        ).simulate(
            make_gateway(), reference_price="100", liquidity_slices=["10", "40"]
        )
        self.assertEqual("2.0000", result.orders[0]["total_commission"])

    def test_gross_notional(self):
        result = self.simulator(slippage_bps="0").simulate(
            make_gateway(), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("5000.0000", result.orders[0]["gross_notional"])

    def test_multiple_orders(self):
        orders = [
            make_order(broker_order_id="paper-1", child_order_id="c1"),
            make_order(broker_order_id="paper-2", child_order_id="c2"),
        ]
        result = self.simulator().simulate(
            make_gateway(orders), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual(2, result.order_count)
        self.assertEqual(2, result.fully_filled_count)

    def test_gateway_status_rejected(self):
        result = self.simulator().simulate(
            make_gateway(status="FAIL"),
            reference_price="100",
            liquidity_slices=["50"],
        )
        self.assertEqual("FAIL", result.status)

    def test_gateway_decision_rejected(self):
        result = self.simulator().simulate(
            make_gateway(decision="reject"),
            reference_price="100",
            liquidity_slices=["50"],
        )
        self.assertEqual("FAIL", result.status)

    def test_gateway_network_rejected(self):
        result = self.simulator().simulate(
            make_gateway(network_used=True),
            reference_price="100",
            liquidity_slices=["50"],
        )
        self.assertEqual("FAIL", result.status)

    def test_gateway_rejections_rejected(self):
        result = self.simulator().simulate(
            make_gateway(rejection_reasons=["bad"]),
            reference_price="100",
            liquidity_slices=["50"],
        )
        self.assertEqual("FAIL", result.status)

    def test_gateway_count_mismatch(self):
        result = self.simulator().simulate(
            make_gateway(accepted_count=2),
            reference_price="100",
            liquidity_slices=["50"],
        )
        self.assertEqual("FAIL", result.status)

    def test_gateway_hash_tamper(self):
        gateway = make_gateway()
        tampered = GatewayInput(**{**asdict(gateway), "status": "FAIL"})
        result = self.simulator().simulate(
            tampered, reference_price="100", liquidity_slices=["50"]
        )
        self.assertIn(
            "V47 gateway SHA-256 verification failed.",
            result.rejection_reasons,
        )

    def test_order_hash_tamper(self):
        order = make_order()
        order["quantity"] = "51"
        result = self.simulator().simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("FAIL", result.status)

    def test_order_status_rejected(self):
        order = make_order(status="WORKING")
        result = self.simulator().simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("FAIL", result.status)

    def test_order_network_rejected(self):
        order = make_order(network_used=True)
        result = self.simulator().simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("FAIL", result.status)

    def test_invalid_order_type(self):
        order = make_order(order_type="stop")
        result = self.simulator().simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("FAIL", result.status)

    def test_invalid_limit_price(self):
        order = make_order(order_type="limit", limit_price="0")
        result = self.simulator().simulate(
            make_gateway([order]), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual("FAIL", result.status)

    def test_invalid_reference_price(self):
        result = self.simulator().simulate(
            make_gateway(), reference_price="0", liquidity_slices=["50"]
        )
        self.assertEqual("FAIL", result.status)

    def test_negative_liquidity(self):
        result = self.simulator().simulate(
            make_gateway(), reference_price="100", liquidity_slices=["-1"]
        )
        self.assertEqual("FAIL", result.status)

    def test_negative_slippage_rejected(self):
        with self.assertRaises(ValueError):
            self.simulator(slippage_bps="-1")

    def test_negative_commission_rejected(self):
        with self.assertRaises(ValueError):
            self.simulator(commission_per_share="-1")

    def test_negative_minimum_commission_rejected(self):
        with self.assertRaises(ValueError):
            self.simulator(minimum_commission="-1")

    def test_deterministic_hash(self):
        first = self.simulator().simulate(
            make_gateway(), reference_price="100", liquidity_slices=["50"]
        )
        second = self.simulator().simulate(
            make_gateway(), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual(first.simulation_sha256, second.simulation_sha256)

    def test_fill_hash_present(self):
        result = self.simulator().simulate(
            make_gateway(), reference_price="100", liquidity_slices=["50"]
        )
        self.assertEqual(64, len(result.orders[0]["fills"][0]["fill_sha256"]))

    def test_ledger_hash_chain(self):
        result = self.simulator().simulate(
            make_gateway(), reference_price="100", liquidity_slices=["20", "30"]
        )
        ledger = result.ledger
        self.assertEqual("GENESIS", ledger[0]["previous_entry_sha256"])
        for left, right in zip(ledger, ledger[1:]):
            self.assertEqual(
                left["entry_sha256"],
                right["previous_entry_sha256"],
            )

    def test_network_false(self):
        result = self.simulator().simulate(
            make_gateway(), reference_price="100", liquidity_slices=["50"]
        )
        self.assertFalse(result.network_used)
        self.assertFalse(result.orders[0]["fills"][0]["network_used"])

    def test_export(self):
        simulator = self.simulator()
        result = simulator.simulate(
            make_gateway(), reference_price="100", liquidity_slices=["50"]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fill.json"
            simulator.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])
            self.assertFalse(payload["network_used"])

    def test_load_gateway_export_shape(self):
        gateway = make_gateway()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gateway.json"
            path.write_text(
                json.dumps({"result": asdict(gateway)}),
                encoding="utf-8",
            )
            loaded = load_gateway(path)
            self.assertEqual(gateway, loaded)

    def test_live_gate(self):
        simulator = PaperFillSimulator(mode="live")
        with self.assertRaises(PermissionError):
            simulator.simulate(
                make_gateway(),
                reference_price="100",
                liquidity_slices=["50"],
            )

    def test_live_transport_not_implemented(self):
        simulator = PaperFillSimulator(mode="live", enable_live=True)
        with self.assertRaises(NotImplementedError):
            simulator.simulate(
                make_gateway(),
                reference_price="100",
                liquidity_slices=["50"],
            )

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            PaperFillSimulator(mode="bad")


if __name__ == "__main__":
    unittest.main()
