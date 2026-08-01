from __future__ import annotations

import unittest

from autonomous_paper_runtime import (
    AutonomousAlpacaPaperRuntime,
    AutonomousDecision,
    AutonomousRuntimeConfig,
)


class MarketReader:
    def __init__(self, *, open_=True, price=50.0):
        self.open_ = open_
        self.price = price

    def is_market_open(self):
        return self.open_

    def get_price(self, symbol):
        return self.price


class SignalProvider:
    def __init__(self, action="BUY"):
        self.action = action

    def get_signal(self, symbol):
        return self.action


class PreviewBuilder:
    def build(self, *, symbol, quantity, estimated_price):
        return {
            "symbol": symbol,
            "qty": quantity,
            "estimated_price": estimated_price,
            "client_order_id": "BOT-AUTO-PAPER-ONE-000001",
        }


class Submitter:
    def __init__(self):
        self.calls = 0

    def submit(self, preview):
        self.calls += 1
        return {"client_order_id": preview["client_order_id"], "status": "accepted"}


class AutonomousAlpacaPaperRuntimeTests(unittest.TestCase):
    def make_runtime(self, config=None, reader=None, signal=None, submitter=None):
        return AutonomousAlpacaPaperRuntime(
            config=config or AutonomousRuntimeConfig(),
            market_reader=reader or MarketReader(),
            signal_provider=signal or SignalProvider(),
            order_preview_builder=PreviewBuilder(),
            single_order_submitter=submitter,
        )

    def test_config_default_safe(self):
        config = AutonomousRuntimeConfig()
        config.validate()
        self.assertFalse(config.read_network_enabled)
        self.assertFalse(config.single_order_write_enabled)
        self.assertFalse(config.live_trading_enabled)

    def test_live_trading_rejected(self):
        with self.assertRaises(ValueError):
            AutonomousRuntimeConfig(live_trading_enabled=True).validate()

    def test_write_requires_read(self):
        with self.assertRaises(ValueError):
            AutonomousRuntimeConfig(single_order_write_enabled=True).validate()

    def test_start(self):
        runtime = self.make_runtime()
        runtime.start()
        self.assertEqual(runtime.state.value, "READY")

    def test_market_closed_wait(self):
        runtime = self.make_runtime(reader=MarketReader(open_=False))
        runtime.start()
        result = runtime.run_cycle()
        self.assertEqual(result.decision, AutonomousDecision.WAIT_MARKET_CLOSED)

    def test_no_signal_wait(self):
        runtime = self.make_runtime(signal=SignalProvider("HOLD"))
        runtime.start()
        result = runtime.run_cycle()
        self.assertEqual(result.decision, AutonomousDecision.WAIT_NO_SIGNAL)

    def test_read_disabled_blocks(self):
        runtime = self.make_runtime()
        runtime.start()
        result = runtime.run_cycle()
        self.assertEqual(result.decision, AutonomousDecision.BLOCKED_READ_DISABLED)
        self.assertEqual(result.read_requests_executed, 0)

    def test_read_enabled_preview_only(self):
        config = AutonomousRuntimeConfig(read_network_enabled=True)
        runtime = self.make_runtime(config=config)
        runtime.start()
        result = runtime.run_cycle()
        self.assertEqual(result.decision, AutonomousDecision.PREVIEW_ORDER)
        self.assertEqual(result.read_requests_executed, 2)
        self.assertEqual(result.write_requests_executed, 0)
        self.assertEqual(result.actual_paper_orders_submitted, 0)

    def test_notional_cap_blocks_write(self):
        config = AutonomousRuntimeConfig(
            read_network_enabled=True,
            single_order_write_enabled=True,
        )
        runtime = self.make_runtime(config=config, reader=MarketReader(price=150.0), submitter=Submitter())
        runtime.start()
        result = runtime.run_cycle()
        self.assertEqual(result.decision, AutonomousDecision.BLOCKED_WRITE_DISABLED)
        self.assertEqual(result.actual_paper_orders_submitted, 0)

    def test_single_order_opt_in(self):
        config = AutonomousRuntimeConfig(
            read_network_enabled=True,
            single_order_write_enabled=True,
        )
        submitter = Submitter()
        runtime = self.make_runtime(config=config, submitter=submitter)
        runtime.start()
        result = runtime.run_cycle()
        self.assertEqual(result.decision, AutonomousDecision.SUBMIT_SINGLE_PAPER_ORDER)
        self.assertEqual(result.write_requests_executed, 1)
        self.assertEqual(result.actual_paper_orders_submitted, 1)
        self.assertEqual(submitter.calls, 1)

    def test_missing_submitter_rejected(self):
        config = AutonomousRuntimeConfig(
            read_network_enabled=True,
            single_order_write_enabled=True,
        )
        runtime = self.make_runtime(config=config)
        runtime.start()
        with self.assertRaises(RuntimeError):
            runtime.run_cycle()

    def test_stop(self):
        runtime = self.make_runtime()
        runtime.start()
        runtime.stop()
        self.assertEqual(runtime.state.value, "STOPPED")

    def test_duplicate_start_rejected(self):
        runtime = self.make_runtime()
        runtime.start()
        with self.assertRaises(RuntimeError):
            runtime.start()

    def test_live_orders_always_zero(self):
        runtime = self.make_runtime(config=AutonomousRuntimeConfig(read_network_enabled=True))
        runtime.start()
        result = runtime.run_cycle()
        self.assertEqual(result.live_orders_submitted, 0)


if __name__ == "__main__":
    unittest.main()
