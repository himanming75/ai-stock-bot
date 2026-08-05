from __future__ import annotations
import unittest

from paper_dispatch_engine.simulator import simulate_fill
from paper_dispatch_engine.simulator_guard import run_paper_execution_simulator


def local_order():
    return {
        "local_execution_id": "execution-001",
        "dispatch_id": "dispatch-001",
        "proposal_id": "proposal-001",
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "MARKET",
        "estimated_notional": 1000,
        "time_in_force": "day",
        "target_environment": "PAPER",
        "broker_adapter": "NONE",
        "submission_state": "ACCEPTED_FOR_SIMULATION",
    }


def market():
    return {
        "symbol": "AAPL",
        "reference_price": 100.0,
        "available_quantity": 100.0,
    }


def policy():
    return {
        "slippage_bps": 10,
        "fill_ratio": 1.0,
    }


def dispatch_result():
    return {
        "stage": "V392.10A",
        "state": "LOCAL_PAPER_DISPATCH_ENGINE_READY",
        "status": "PASS",
        "local_dispatch_accepted": True,
        "paper_execution_simulator_allowed": True,
        "broker_network_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
    }


class Tests(unittest.TestCase):
    def test_full_fill(self):
        result = simulate_fill(local_order(), market(), policy(), set())
        self.assertTrue(result["approved"])
        self.assertEqual(result["fill_event"]["fill_state"], "FILLED")

    def test_partial_fill(self):
        value = market()
        value["available_quantity"] = 2.0
        result = simulate_fill(local_order(), value, policy(), set())
        self.assertEqual(result["fill_event"]["fill_state"], "PARTIALLY_FILLED")

    def test_no_fill(self):
        value = market()
        value["available_quantity"] = 0.0
        result = simulate_fill(local_order(), value, policy(), set())
        self.assertEqual(result["fill_event"]["fill_state"], "NO_FILL")

    def test_sell_slippage(self):
        order = local_order()
        order["side"] = "SELL"
        result = simulate_fill(order, market(), policy(), set())
        self.assertLess(result["fill_event"]["fill_price"], 100.0)

    def test_replay_rejected(self):
        result = simulate_fill(
            local_order(), market(), policy(), {"execution-001"}
        )
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["approved"])

    def test_symbol_mismatch(self):
        value = market()
        value["symbol"] = "MSFT"
        result = simulate_fill(local_order(), value, policy(), set())
        self.assertFalse(result["approved"])

    def test_invalid_policy(self):
        value = policy()
        value["fill_ratio"] = 2.0
        result = simulate_fill(local_order(), market(), value, set())
        self.assertFalse(result["approved"])

    def test_zero_orders(self):
        result = run_paper_execution_simulator(
            dispatch_result(),
            local_order(),
            market(),
            policy(),
            set(),
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)
        self.assertEqual(
            result["evaluation"]["actual_broker_orders_submitted"], 0
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
