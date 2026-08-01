from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from runtime_engine import Event, EventBus, ManualClock
from execution_engine import (
    AlpacaPaperPayloadBuilder,
    CancelRequest,
    ClientOrderIdGenerator,
    DuplicateIntentGuard,
    ExecutionIdempotencyGuard,
    ExecutionStatus,
    IntentExpiryPolicy,
    MockPaperTransport,
    OrderIntent,
    OrderSide,
    OrderType,
    PaperExecutionAdapter,
    PaperExecutionEngine,
    TimeInForce,
)


class PaperExecutionAdapterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
        self.intent = OrderIntent(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            reference_price=Decimal("50"),
            estimated_notional=Decimal("50"),
            created_at=self.now,
            expires_at=self.now + timedelta(seconds=30),
            source_signal_id="sig-1",
            strategy_name="demo",
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        )

    def adapter(self, transport=None):
        return PaperExecutionAdapter(
            transport=transport or MockPaperTransport(),
            payload_builder=AlpacaPaperPayloadBuilder(),
            client_order_id_generator=ClientOrderIdGenerator(),
            idempotency_guard=ExecutionIdempotencyGuard(),
        )

    def test_client_order_id(self):
        generator = ClientOrderIdGenerator()
        self.assertEqual(generator.next_id(self.now), "BOT-20260801-000001")
        self.assertEqual(generator.next_id(self.now), "BOT-20260801-000002")

    def test_payload_builder_market(self):
        payload = AlpacaPaperPayloadBuilder().build(self.intent, "BOT-1")
        self.assertEqual(payload["symbol"], "AAPL")
        self.assertEqual(payload["side"], "buy")
        self.assertNotIn("limit_price", payload)

    def test_payload_builder_limit(self):
        intent = OrderIntent(**{**self.intent.__dict__, "order_type":OrderType.LIMIT, "limit_price":Decimal("49.5")})
        payload = AlpacaPaperPayloadBuilder().build(intent, "BOT-1")
        self.assertEqual(payload["limit_price"], "49.5")

    def test_idempotency_guard(self):
        guard = ExecutionIdempotencyGuard()
        self.assertTrue(guard.register(intent_id="i1", client_order_id="c1"))
        self.assertFalse(guard.register(intent_id="i1", client_order_id="c2"))
        self.assertFalse(guard.register(intent_id="i2", client_order_id="c1"))

    def test_adapter_build_request(self):
        request = self.adapter().build_request(self.intent, self.now)
        self.assertEqual(request.symbol, "AAPL")
        self.assertEqual(request.payload["client_order_id"], request.client_order_id)

    def test_mock_transport_accepts(self):
        request, result = self.adapter().submit(self.intent, self.now)
        self.assertEqual(result.status, ExecutionStatus.ACCEPTED)
        self.assertEqual(result.client_order_id, request.client_order_id)

    def test_mock_transport_rejects_symbol(self):
        adapter = self.adapter(MockPaperTransport(reject_symbols={"AAPL"}))
        _, result = adapter.submit(self.intent, self.now)
        self.assertEqual(result.status, ExecutionStatus.REJECTED)
        self.assertIsNotNone(result.rejection_reason)

    def test_partial_fill(self):
        transport = MockPaperTransport()
        adapter = self.adapter(transport)
        request, _ = adapter.submit(self.intent, self.now)
        partial = transport.simulate_partial_fill(request.client_order_id, self.now + timedelta(seconds=1))
        self.assertEqual(partial.status, ExecutionStatus.PARTIALLY_FILLED)
        self.assertEqual(partial.filled_quantity, Decimal("0.5"))

    def test_full_fill_after_partial(self):
        transport = MockPaperTransport()
        adapter = self.adapter(transport)
        request, _ = adapter.submit(self.intent, self.now)
        transport.simulate_partial_fill(request.client_order_id, self.now + timedelta(seconds=1))
        filled = transport.simulate_full_fill(request.client_order_id, self.now + timedelta(seconds=2))
        self.assertEqual(filled.status, ExecutionStatus.FILLED)
        self.assertEqual(filled.filled_quantity, Decimal("1"))

    def test_cancel(self):
        adapter = self.adapter()
        _, result = adapter.submit(self.intent, self.now)
        canceled = adapter.cancel(result.client_order_id, self.now + timedelta(seconds=1))
        self.assertEqual(canceled.status, ExecutionStatus.CANCELED)

    def test_reconciliation_match(self):
        adapter = self.adapter()
        _, result = adapter.submit(self.intent, self.now)
        record = adapter.reconcile(
            request_status=ExecutionStatus.ACCEPTED,
            transport_result=result,
            now=self.now,
        )
        self.assertTrue(record.matched)

    def test_reconciliation_mismatch(self):
        adapter = self.adapter()
        _, result = adapter.submit(self.intent, self.now)
        record = adapter.reconcile(
            request_status=ExecutionStatus.FILLED,
            transport_result=result,
            now=self.now,
        )
        self.assertFalse(record.matched)

    def test_event_bus_execution_flow(self):
        bus = EventBus()
        clock = ManualClock(self.now)
        requests = []
        updates = []
        bus.subscribe("execution.request", lambda event: requests.append(event.payload["request"]))
        bus.subscribe("execution.update", lambda event: updates.append(event.payload["result"]))
        engine = PaperExecutionEngine(event_bus=bus, adapter=self.adapter(), now=clock.now)
        engine.start()
        bus.publish(Event("order.intent", {"intent":self.intent}, self.now))
        engine.stop()
        self.assertEqual(len(requests), 1)
        self.assertEqual(len(updates), 1)
        self.assertEqual(engine.stats.accepted, 1)

    def test_event_bus_rejected_flow(self):
        bus = EventBus()
        clock = ManualClock(self.now)
        engine = PaperExecutionEngine(
            event_bus=bus,
            adapter=self.adapter(MockPaperTransport(reject_symbols={"AAPL"})),
            now=clock.now,
        )
        engine.start()
        bus.publish(Event("order.intent", {"intent":self.intent}, self.now))
        engine.stop()
        self.assertEqual(engine.stats.rejected, 1)

    def test_no_network_transport(self):
        transport = MockPaperTransport()
        adapter = self.adapter(transport)
        adapter.submit(self.intent, self.now)
        self.assertEqual(len(transport.requests), 1)


if __name__ == "__main__":
    unittest.main()
