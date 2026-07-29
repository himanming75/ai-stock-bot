import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.trade_execution_coordinator_v57_0 import (
    BrokerEvent,
    ExecutionConfig,
    ExecutionRequest,
    TradeExecutionCoordinator,
    load_payload,
)


def req(**overrides):
    data = dict(
        request_id="exec-1",
        symbol="AAPL",
        action="BUY",
        quantity="100",
        limit_price="200",
        risk_approval_sha256="a" * 64,
        submitted_at_utc="2026-07-29T16:00:00Z",
        execution_key="AAPL-BUY-100-200",
        metadata={},
    )
    data.update(overrides)
    return ExecutionRequest(**data)


def cfg(**overrides):
    data = dict(
        max_retries=2,
        timeout_seconds=60,
        allow_partial_fills=True,
        cancel_on_timeout=True,
    )
    data.update(overrides)
    return ExecutionConfig(**data)


def evt(event_type, sec=1, filled_quantity="0", fill_price="0", reason=""):
    return BrokerEvent(
        event_type=event_type,
        event_time_utc=f"2026-07-29T16:00:{sec:02d}Z",
        filled_quantity=filled_quantity,
        fill_price=fill_price,
        reason=reason,
    )


class TradeExecutionCoordinatorV570Tests(unittest.TestCase):
    def engine(self):
        return TradeExecutionCoordinator(mode="paper")

    def test_full_fill(self):
        r = self.engine().coordinate(req(), cfg(), [evt("FILL", 1, "100", "199.50")])
        self.assertEqual("FILLED", r.final_state)

    def test_full_fill_pass(self):
        r = self.engine().coordinate(req(), cfg(), [evt("FILL", 1, "100", "199.50")])
        self.assertEqual("PASS", r.status)

    def test_full_fill_decision(self):
        r = self.engine().coordinate(req(), cfg(), [evt("FILL", 1, "100", "199.50")])
        self.assertEqual("execution_completed", r.decision)

    def test_avg_price(self):
        r = self.engine().coordinate(req(), cfg(), [
            evt("PARTIAL_FILL", 1, "40", "199"),
            evt("FILL", 2, "60", "201"),
        ])
        self.assertEqual("200.20", r.average_fill_price)

    def test_partial_fill(self):
        r = self.engine().coordinate(req(), cfg(), [evt("PARTIAL_FILL", 1, "40", "199")])
        self.assertEqual("PARTIALLY_FILLED", r.final_state)

    def test_partial_fill_decision(self):
        r = self.engine().coordinate(req(), cfg(), [evt("PARTIAL_FILL", 1, "40", "199")])
        self.assertEqual("execution_partially_filled", r.decision)

    def test_partial_disabled(self):
        r = self.engine().coordinate(req(), cfg(allow_partial_fills=False), [evt("PARTIAL_FILL", 1, "40", "199")])
        self.assertIn("partial_fills_disabled", r.rejection_reasons)

    def test_duplicate(self):
        r = self.engine().coordinate(req(), cfg(), [], {"AAPL-BUY-100-200"})
        self.assertIn("duplicate_execution", r.rejection_reasons)

    def test_retry_then_fill(self):
        r = self.engine().coordinate(req(), cfg(), [
            evt("RETRYABLE_ERROR", 1, reason="temporary"),
            evt("FILL", 2, "100", "200"),
        ])
        self.assertEqual(1, r.retry_count)
        self.assertEqual("FILLED", r.final_state)

    def test_max_retries(self):
        r = self.engine().coordinate(req(), cfg(max_retries=1), [
            evt("RETRYABLE_ERROR", 1),
            evt("RETRYABLE_ERROR", 2),
        ])
        self.assertIn("max_retries_exceeded", r.rejection_reasons)

    def test_timeout_cancel(self):
        late = BrokerEvent("ACK", "2026-07-29T16:02:00Z", "0", "0", "")
        r = self.engine().coordinate(req(), cfg(timeout_seconds=30, cancel_on_timeout=True), [late])
        self.assertEqual("CANCELLED", r.final_state)
        self.assertTrue(r.timed_out)

    def test_timeout_no_cancel(self):
        late = BrokerEvent("ACK", "2026-07-29T16:02:00Z", "0", "0", "")
        r = self.engine().coordinate(req(), cfg(timeout_seconds=30, cancel_on_timeout=False), [late])
        self.assertEqual("TIMED_OUT", r.final_state)

    def test_cancel_request(self):
        r = self.engine().coordinate(req(), cfg(), [evt("CANCEL_REQUEST", 1, reason="user")])
        self.assertEqual("CANCEL_REQUESTED", r.final_state)
        self.assertTrue(r.cancel_requested)

    def test_cancelled(self):
        r = self.engine().coordinate(req(), cfg(), [evt("CANCEL_REQUEST", 1), evt("CANCELLED", 2)])
        self.assertEqual("CANCELLED", r.final_state)

    def test_broker_reject(self):
        r = self.engine().coordinate(req(), cfg(), [evt("REJECT", 1, reason="broker_rejected")])
        self.assertEqual("REJECTED", r.final_state)

    def test_overfill(self):
        r = self.engine().coordinate(req(), cfg(), [evt("FILL", 1, "101", "200")])
        self.assertIn("overfill_detected", r.rejection_reasons)

    def test_zero_fill(self):
        r = self.engine().coordinate(req(), cfg(), [evt("FILL", 1, "0", "200")])
        self.assertIn("fill_quantity_must_be_positive", r.rejection_reasons)

    def test_zero_fill_price(self):
        r = self.engine().coordinate(req(), cfg(), [evt("FILL", 1, "100", "0")])
        self.assertIn("fill_price_must_be_positive", r.rejection_reasons)

    def test_unsupported_event(self):
        r = self.engine().coordinate(req(), cfg(), [evt("UNKNOWN", 1)])
        self.assertIn("unsupported_broker_event", r.rejection_reasons)

    def test_out_of_order_events(self):
        events = [
            BrokerEvent("ACK", "2026-07-29T16:00:10Z", "0", "0", ""),
            BrokerEvent("FILL", "2026-07-29T16:00:05Z", "100", "200", ""),
        ]
        r = self.engine().coordinate(req(), cfg(), events)
        self.assertIn("broker_event_time_out_of_order", r.rejection_reasons)

    def test_pending_without_events(self):
        r = self.engine().coordinate(req(), cfg(), [])
        self.assertEqual("SUBMITTED", r.final_state)

    def test_order_id_deterministic(self):
        a = self.engine().coordinate(req(), cfg(), [])
        b = self.engine().coordinate(req(), cfg(), [])
        self.assertEqual(a.order_id, b.order_id)

    def test_execution_id_deterministic(self):
        a = self.engine().coordinate(req(), cfg(), [])
        b = self.engine().coordinate(req(), cfg(), [])
        self.assertEqual(a.execution_id, b.execution_id)

    def test_request_hash(self):
        r = self.engine().coordinate(req(), cfg(), [])
        self.assertEqual(64, len(r.request_sha256))

    def test_execution_hash(self):
        r = self.engine().coordinate(req(), cfg(), [])
        self.assertEqual(64, len(r.execution_sha256))

    def test_network_false(self):
        r = self.engine().coordinate(req(), cfg(), [])
        self.assertFalse(r.network_used)

    def test_ledger_genesis(self):
        r = self.engine().coordinate(req(), cfg(), [])
        self.assertEqual("GENESIS", r.ledger[0]["previous_entry_sha256"])

    def test_ledger_chain(self):
        r = self.engine().coordinate(req(), cfg(), [evt("ACK", 1), evt("FILL", 2, "100", "200")])
        self.assertEqual(r.ledger[0]["entry_sha256"], r.ledger[1]["previous_entry_sha256"])

    def test_symbol_uppercase(self):
        r = self.engine().coordinate(req(symbol="aapl"), cfg(), [])
        self.assertEqual("AAPL", r.symbol)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            TradeExecutionCoordinator(mode="bad")

    def test_live_blocked(self):
        with self.assertRaises(PermissionError):
            TradeExecutionCoordinator(mode="live").coordinate(req(), cfg(), [])

    def test_live_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            TradeExecutionCoordinator(mode="live", enable_live=True).coordinate(req(), cfg(), [])

    def test_bad_request_id(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(request_id=""), cfg(), [])

    def test_bad_symbol(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(symbol=""), cfg(), [])

    def test_bad_action(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(action="HOLD"), cfg(), [])

    def test_bad_quantity(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(quantity="0"), cfg(), [])

    def test_bad_price(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(limit_price="0"), cfg(), [])

    def test_bad_hash(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(risk_approval_sha256="x"), cfg(), [])

    def test_bad_execution_key(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(execution_key=""), cfg(), [])

    def test_bad_timestamp(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(submitted_at_utc="bad"), cfg(), [])

    def test_naive_timestamp(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(submitted_at_utc="2026-07-29T16:00:00"), cfg(), [])

    def test_bad_retries(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(), cfg(max_retries=-1), [])

    def test_bad_timeout(self):
        with self.assertRaises(ValueError):
            self.engine().coordinate(req(), cfg(timeout_seconds=0), [])

    def test_remaining_quantity(self):
        r = self.engine().coordinate(req(), cfg(), [evt("PARTIAL_FILL", 1, "40", "199")])
        self.assertEqual("60.000000", r.remaining_quantity)

    def test_filled_quantity(self):
        r = self.engine().coordinate(req(), cfg(), [evt("FILL", 1, "100", "200")])
        self.assertEqual("100.000000", r.filled_quantity)

    def test_audit_trail(self):
        r = self.engine().coordinate(req(), cfg(), [evt("ACK", 1), evt("FILL", 2, "100", "200")])
        self.assertGreaterEqual(len(r.audit_trail), 4)

    def test_export(self):
        e = self.engine()
        r = e.coordinate(req(), cfg(), [evt("FILL", 1, "100", "200")])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.json"
            e.export(p, r)
            payload = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])

    def test_load_payload(self):
        payload = {
            "request": asdict(req()),
            "config": asdict(cfg()),
            "broker_events": [asdict(evt("FILL", 1, "100", "200"))],
            "seen_execution_keys": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "in.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            r, c, events, seen = load_payload(p)
            self.assertEqual("exec-1", r.request_id)
            self.assertEqual(2, c.max_retries)
            self.assertEqual(1, len(events))
            self.assertEqual(set(), seen)


if __name__ == "__main__":
    unittest.main()
