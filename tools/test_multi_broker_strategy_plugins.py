from __future__ import annotations
import unittest

from multi_broker_plugins.brokers import BrokerRegistry
from multi_broker_plugins.strategies import StrategyRegistry
from multi_broker_plugins.versioning import StrategyHotSwapPreview


class Tests(unittest.TestCase):
    def test_six_brokers(self):
        self.assertEqual(len(BrokerRegistry().list_capabilities()), 6)

    def test_broker_network_blocked(self):
        with self.assertRaises(RuntimeError):
            BrokerRegistry().get("alpaca").connect()

    def test_five_strategies(self):
        self.assertEqual(len(StrategyRegistry().list_metadata()), 5)

    def test_strategy_creates_no_order(self):
        result = StrategyRegistry().get("momentum_v3").evaluate({
            "momentum": "0.05"
        })
        self.assertFalse(result["order_created"])

    def test_hot_swap_preview(self):
        result = StrategyHotSwapPreview().preview(
            current_strategy="momentum_v3",
            target_strategy="swing_v1",
            open_positions=0,
            open_orders=0,
        )
        self.assertTrue(result["hot_swap_preview_allowed"])
        self.assertFalse(result["actual_hot_swap_performed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
