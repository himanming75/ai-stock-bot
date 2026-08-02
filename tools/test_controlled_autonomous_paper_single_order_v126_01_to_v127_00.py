from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import unittest

from autonomous_paper_runtime.controlled_single_order import (
    ControlledAutonomousPaperSingleOrder,
    ControlledOrderDecision,
    ControlledSingleOrderRequest,
)


@dataclass
class Account:
    status: str = "ACTIVE"
    trading_blocked: bool = False


@dataclass
class Clock:
    is_open: bool = True


@dataclass
class Order:
    order_id: str = "paper-order-1"
    status: str = "accepted"


class Broker:
    def __init__(self, *, open_orders=(), market_open=True):
        self.open_orders = tuple(open_orders)
        self.market_open = market_open
        self.network_requests_executed = 0
        self.write_requests_executed = 0
        self.submissions = []

    def get_account(self):
        self.network_requests_executed += 1
        return Account()

    def get_clock(self):
        self.network_requests_executed += 1
        return Clock(self.market_open)

    def list_orders(self, *, status="open", limit=50):
        self.network_requests_executed += 1
        return self.open_orders

    def preview_submit_order(self, payload):
        return {"payload": payload, "network_executed": False}

    def submit_order(self, payload):
        self.network_requests_executed += 1
        self.write_requests_executed += 1
        self.submissions.append(payload)
        return Order()


def readiness():
    return {
        "state": "PAPER_WRITE_READY",
        "paper_write_ready": True,
        "approval_token_verified": True,
    }


def request(**overrides):
    values = {
        "symbol": "AAPL",
        "side": "buy",
        "quantity": Decimal("1"),
        "estimated_price": Decimal("50"),
    }
    values.update(overrides)
    return ControlledSingleOrderRequest(**values)


class ControlledSingleOrderTests(unittest.TestCase):
    def setUp(self):
        self.runner = ControlledAutonomousPaperSingleOrder()

    def test_preview_only_without_submission_approval(self):
        broker = Broker()
        result = self.runner.execute(
            broker=broker,
            request=request(),
            readiness_result=readiness(),
            submit_enabled=False,
            approval_text="",
            client_order_nonce="preview",
        )
        self.assertEqual(result.decision, ControlledOrderDecision.PREVIEW_READY)
        self.assertEqual(result.actual_paper_orders_submitted, 0)

    def test_exactly_one_submission(self):
        broker = Broker()
        result = self.runner.execute(
            broker=broker,
            request=request(),
            readiness_result=readiness(),
            submit_enabled=True,
            approval_text=self.runner.APPROVAL_TEXT,
            client_order_nonce="submit",
        )
        self.assertEqual(result.decision, ControlledOrderDecision.SUBMITTED)
        self.assertEqual(len(broker.submissions), 1)
        self.assertEqual(result.actual_paper_orders_submitted, 1)

    def test_existing_order_blocks(self):
        broker = Broker(open_orders=(Order(),))
        result = self.runner.execute(
            broker=broker,
            request=request(),
            readiness_result=readiness(),
            submit_enabled=True,
            approval_text=self.runner.APPROVAL_TEXT,
            client_order_nonce="blocked",
        )
        self.assertEqual(
            result.decision, ControlledOrderDecision.EXISTING_ORDER_WAIT
        )
        self.assertEqual(len(broker.submissions), 0)

    def test_market_closed_blocks(self):
        result = self.runner.execute(
            broker=Broker(market_open=False),
            request=request(),
            readiness_result=readiness(),
            submit_enabled=True,
            approval_text=self.runner.APPROVAL_TEXT,
            client_order_nonce="closed",
        )
        self.assertEqual(result.reason, "market_closed")

    def test_readiness_missing_blocks(self):
        result = self.runner.execute(
            broker=Broker(),
            request=request(),
            readiness_result={},
            submit_enabled=True,
            approval_text=self.runner.APPROVAL_TEXT,
            client_order_nonce="not-ready",
        )
        self.assertEqual(result.reason, "paper_write_readiness_missing")

    def test_wrong_approval_preview_only(self):
        result = self.runner.execute(
            broker=Broker(),
            request=request(),
            readiness_result=readiness(),
            submit_enabled=True,
            approval_text="WRONG",
            client_order_nonce="wrong",
        )
        self.assertEqual(result.decision, ControlledOrderDecision.PREVIEW_READY)

    def test_symbol_blocked(self):
        result = self.runner.execute(
            broker=Broker(),
            request=request(symbol="TSLA"),
            readiness_result=readiness(),
            submit_enabled=False,
            approval_text="",
            client_order_nonce="symbol",
        )
        self.assertEqual(result.reason, "symbol_not_allowed")

    def test_quantity_cap(self):
        result = self.runner.execute(
            broker=Broker(),
            request=request(quantity=Decimal("2")),
            readiness_result=readiness(),
            submit_enabled=False,
            approval_text="",
            client_order_nonce="qty",
        )
        self.assertEqual(result.reason, "quantity_limit")

    def test_notional_cap(self):
        result = self.runner.execute(
            broker=Broker(),
            request=request(estimated_price=Decimal("101")),
            readiness_result=readiness(),
            submit_enabled=False,
            approval_text="",
            client_order_nonce="notional",
        )
        self.assertEqual(result.reason, "notional_limit")

    def test_market_order_only(self):
        item = ControlledSingleOrderRequest(
            symbol="AAPL", side="buy", quantity=Decimal("1"),
            estimated_price=Decimal("50"), order_type="limit"
        )
        result = self.runner.execute(
            broker=Broker(), request=item, readiness_result=readiness(),
            submit_enabled=False, approval_text="", client_order_nonce="limit"
        )
        self.assertEqual(result.reason, "only_market_order_allowed")

    def test_day_tif_only(self):
        item = ControlledSingleOrderRequest(
            symbol="AAPL", side="buy", quantity=Decimal("1"),
            estimated_price=Decimal("50"), time_in_force="gtc"
        )
        result = self.runner.execute(
            broker=Broker(), request=item, readiness_result=readiness(),
            submit_enabled=False, approval_text="", client_order_nonce="gtc"
        )
        self.assertEqual(result.reason, "only_day_tif_allowed")

    def test_deterministic_client_order_id(self):
        kwargs = dict(
            broker=Broker(), request=request(), readiness_result=readiness(),
            submit_enabled=False, approval_text="", client_order_nonce="same"
        )
        one = self.runner.execute(**kwargs)
        two = self.runner.execute(**kwargs)
        self.assertEqual(one.client_order_id, two.client_order_id)

    def test_live_always_zero(self):
        result = self.runner.execute(
            broker=Broker(), request=request(), readiness_result=readiness(),
            submit_enabled=False, approval_text="", client_order_nonce="live"
        )
        self.assertFalse(result.live_trading_enabled)
        self.assertEqual(result.live_orders_submitted, 0)

    def test_json(self):
        result = self.runner.execute(
            broker=Broker(), request=request(), readiness_result=readiness(),
            submit_enabled=False, approval_text="", client_order_nonce="json"
        )
        self.assertEqual(result.to_json_dict()["decision"], "PREVIEW_READY")


if __name__ == "__main__":
    unittest.main()
