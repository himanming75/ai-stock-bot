from __future__ import annotations
from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from alpaca_paper_read.config import PAPER_BASE_URL
from broker_integration.execution_config import ExecutionConfig
from broker_integration.execution_models import CanonicalOrderRequest
from broker_integration.execution_service import submit_paper_order


class FakeHttp:
    def submit_order(self, payload):
        return {
            "id": "paper-123",
            "client_order_id": payload["client_order_id"],
            "status": "accepted",
        }, "request-123"


def config(**changes):
    base = dict(
        api_key="key",
        secret_key="secret",
        base_url=PAPER_BASE_URL,
        network_enabled=True,
        write_enabled=True,
        confirmation="I_UNDERSTAND_THIS_SUBMITS_A_PAPER_ORDER",
        maximum_order_notional=Decimal("10"),
        maximum_daily_orders=3,
        allowed_symbols=frozenset({"AAPL"}),
        timeout_seconds=1,
        maximum_attempts=1,
        backoff_seconds=0,
    )
    base.update(changes)
    return ExecutionConfig(**base)


def order(**changes):
    base = dict(
        symbol="AAPL",
        side="buy",
        order_type="market",
        time_in_force="day",
        notional=Decimal("5"),
        client_order_id="p2-test-order-001",
    )
    base.update(changes)
    return CanonicalOrderRequest(**base)


def common_kwargs(directory: str, **changes):
    value = dict(
        config=config(),
        order=order(),
        account={
            "status": "ACTIVE",
            "account_blocked": False,
            "trading_blocked": False,
            "buying_power": "1000",
        },
        asset={"status": "active", "tradable": True},
        clock={"is_open": True},
        kill_switch={"kill_switch_active": False},
        risk_permission=True,
        latest_trade_price=None,
        positions=[],
        registry_path=Path(directory) / "registry.json",
        order_ledger_path=Path(directory) / "orders.jsonl",
        error_ledger_path=Path(directory) / "errors.jsonl",
        http=FakeHttp(),
    )
    value.update(changes)
    return value


class Tests(unittest.TestCase):
    def test_market_notional_order_valid(self):
        order().validate()

    def test_limit_fractional_rejected(self):
        with self.assertRaises(ValueError):
            order(
                order_type="limit",
                notional=None,
                qty=Decimal("0.5"),
                limit_price=Decimal("200"),
            ).validate()

    def test_limit_whole_qty_valid(self):
        order(
            order_type="limit",
            notional=None,
            qty=Decimal("1"),
            limit_price=Decimal("5"),
        ).validate()

    def test_live_endpoint_impossible_in_config_object_check(self):
        self.assertFalse(
            config(base_url="https://api.alpaca.markets")
            .paper_endpoint_enforced
        )

    def test_kill_switch_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            result = submit_paper_order(
                **common_kwargs(
                    directory,
                    kill_switch={"kill_switch_active": True},
                )
            )
        self.assertFalse(result["submitted"])
        self.assertIn(
            "kill_switch_inactive",
            result["pre_submit"]["failed"],
        )

    def test_market_closed_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            result = submit_paper_order(
                **common_kwargs(
                    directory,
                    clock={"is_open": False},
                )
            )
        self.assertFalse(result["submitted"])
        self.assertIn("market_open", result["pre_submit"]["failed"])

    def test_order_limit_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            result = submit_paper_order(
                **common_kwargs(
                    directory,
                    order=order(notional=Decimal("11")),
                )
            )
        self.assertFalse(result["submitted"])
        self.assertIn(
            "notional_within_limit",
            result["pre_submit"]["failed"],
        )

    def test_successful_offline_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            result = submit_paper_order(
                **common_kwargs(directory)
            )
        self.assertTrue(result["submitted"])
        self.assertEqual(result["actual_paper_orders_submitted"], 1)
        self.assertEqual(result["actual_live_orders_submitted"], 0)

    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            kwargs = common_kwargs(directory)
            submit_paper_order(**kwargs)
            with self.assertRaises(ValueError):
                submit_paper_order(**kwargs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
