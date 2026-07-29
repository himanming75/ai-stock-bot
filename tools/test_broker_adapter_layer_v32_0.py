import importlib.util
import sys
import unittest


MODULE_PATH = __import__("pathlib").Path(__file__).with_name(
    "broker_adapter_layer_v32_0.py"
)
SPEC = importlib.util.spec_from_file_location("broker_adapter_layer_v32_0", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class BrokerAdapterLayerV320Tests(unittest.TestCase):
    def test_registry_contains_all_brokers(self):
        snapshot = MOD.registry_snapshot()
        self.assertEqual(
            set(snapshot["brokers"]),
            {"paper", "ibkr", "alpaca", "tradestation"},
        )

    def test_paper_buy_updates_account(self):
        broker = MOD.PaperBrokerAdapter(starting_cash="1000", market_prices={"AAPL": "100"})
        result = broker.submit_order(MOD.BrokerOrder(
            symbol="AAPL",
            side=MOD.OrderSide.BUY,
            quantity="2",
            order_type=MOD.OrderType.MARKET,
        ))
        self.assertEqual(result.status, "filled")
        account = broker.account_snapshot()
        self.assertEqual(account.cash, "800")
        self.assertEqual(account.positions[0].quantity, "2")

    def test_paper_sell_reduces_position(self):
        broker = MOD.PaperBrokerAdapter(starting_cash="1000", market_prices={"AAPL": "100"})
        broker.submit_order(MOD.BrokerOrder(
            symbol="AAPL",
            side=MOD.OrderSide.BUY,
            quantity="2",
            order_type=MOD.OrderType.MARKET,
        ))
        sell = broker.submit_order(MOD.BrokerOrder(
            symbol="AAPL",
            side=MOD.OrderSide.SELL,
            quantity="1",
            order_type=MOD.OrderType.MARKET,
        ))
        self.assertEqual(sell.status, "filled")
        self.assertEqual(broker.account_snapshot().positions[0].quantity, "1")

    def test_short_selling_is_rejected(self):
        broker = MOD.PaperBrokerAdapter()
        result = broker.submit_order(MOD.BrokerOrder(
            symbol="AAPL",
            side=MOD.OrderSide.SELL,
            quantity="1",
            order_type=MOD.OrderType.MARKET,
        ))
        self.assertEqual(result.status, "rejected")
        self.assertIn("short selling", result.rejection_reason)

    def test_limit_order_can_remain_open(self):
        broker = MOD.PaperBrokerAdapter(market_prices={"AAPL": "100"})
        result = broker.submit_order(MOD.BrokerOrder(
            symbol="AAPL",
            side=MOD.OrderSide.BUY,
            quantity="1",
            order_type=MOD.OrderType.LIMIT,
            limit_price="90",
        ))
        self.assertEqual(result.status, "accepted")
        cancelled = broker.cancel_order(result.broker_order_id)
        self.assertEqual(cancelled.status, "cancelled")

    def test_external_adapter_never_uses_transport(self):
        adapter = MOD.DisabledExternalBrokerAdapter(
            MOD.BrokerName.IBKR,
            MOD.TradingMode.LIVE,
        )
        result = adapter.submit_order(MOD.BrokerOrder(
            symbol="AAPL",
            side=MOD.OrderSide.BUY,
            quantity="1",
            order_type=MOD.OrderType.MARKET,
        ))
        self.assertEqual(result.status, "rejected")
        self.assertFalse(result.live_transport_used)
        self.assertFalse(adapter.capabilities().network_transport_enabled)

    def test_paper_adapter_rejects_live_mode(self):
        with self.assertRaises(ValueError):
            MOD.create_adapter(MOD.BrokerName.PAPER, MOD.TradingMode.LIVE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
