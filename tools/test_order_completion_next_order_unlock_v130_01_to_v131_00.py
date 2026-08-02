from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.completion_unlock_gate import (
    CompletionGateState,
    CompletionLedger,
    OrderCompletionNextOrderUnlockGate,
)


def lifecycle(**overrides):
    value = {
        "client_order_id": "single-legacy",
        "broker_order_id": "broker-1",
        "symbol": "AAPL",
        "side": "BUY",
        "final_status": "ACCEPTED",
        "quantity": "1",
        "final_filled_quantity": "0",
        "final_remaining_quantity": "1",
        "final_position_quantity": "0",
        "average_fill_price": "0",
        "cash": "100000",
        "equity": "100000",
    }
    value.update(overrides)
    return value


class CompletionUnlockGateTests(unittest.TestCase):
    def evaluate(self, data):
        with tempfile.TemporaryDirectory() as temp:
            ledger = CompletionLedger(Path(temp) / "completion.jsonl")
            gate = OrderCompletionNextOrderUnlockGate(ledger=ledger)
            result = gate.evaluate(
                lifecycle_result=data,
                completed_at="2026-08-02T03:00:00+00:00",
            )
            rows = ledger.read_all()
        return result, rows

    def test_active_remains_locked(self):
        result, rows = self.evaluate(lifecycle())
        self.assertEqual(result.state, CompletionGateState.LOCKED_ACTIVE_ORDER)
        self.assertFalse(result.new_order_allowed)
        self.assertEqual(rows, ())

    def test_partial_remains_locked(self):
        result, rows = self.evaluate(lifecycle(
            final_status="PARTIALLY_FILLED",
            final_filled_quantity=".4",
            final_remaining_quantity=".6",
            final_position_quantity=".4",
        ))
        self.assertEqual(result.state, CompletionGateState.LOCKED_PARTIAL_FILL)
        self.assertFalse(result.new_order_allowed)
        self.assertEqual(rows, ())

    def test_invalid_partial_safe_mode(self):
        result, _ = self.evaluate(lifecycle(
            final_status="PARTIALLY_FILLED",
            final_filled_quantity="0",
            final_remaining_quantity="1",
        ))
        self.assertTrue(result.safe_mode_engaged)

    def test_filled_unlocks(self):
        result, rows = self.evaluate(lifecycle(
            final_status="FILLED",
            final_filled_quantity="1",
            final_remaining_quantity="0",
            final_position_quantity="1",
            average_fill_price="50",
            cash="99950",
        ))
        self.assertEqual(result.state, CompletionGateState.UNLOCKED_FILLED)
        self.assertTrue(result.completion_verified)
        self.assertTrue(result.new_order_allowed)
        self.assertTrue(result.ledger_entry_written)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "ORDER_COMPLETED")

    def test_filled_quantity_mismatch_blocks(self):
        result, rows = self.evaluate(lifecycle(
            final_status="FILLED",
            final_filled_quantity=".5",
            final_remaining_quantity=".5",
            final_position_quantity=".5",
        ))
        self.assertTrue(result.safe_mode_engaged)
        self.assertFalse(result.new_order_allowed)
        self.assertEqual(rows, ())

    def test_filled_position_missing_blocks(self):
        result, _ = self.evaluate(lifecycle(
            final_status="FILLED",
            final_filled_quantity="1",
            final_remaining_quantity="0",
            final_position_quantity="0",
        ))
        self.assertTrue(result.safe_mode_engaged)

    def test_canceled_unlocks(self):
        result, rows = self.evaluate(lifecycle(
            final_status="CANCELED",
            final_filled_quantity="0",
            final_remaining_quantity="1",
        ))
        self.assertEqual(
            result.state,
            CompletionGateState.UNLOCKED_TERMINAL_NO_FILL,
        )
        self.assertTrue(result.new_order_allowed)
        self.assertEqual(len(rows), 1)

    def test_expired_unlocks(self):
        result, _ = self.evaluate(lifecycle(final_status="EXPIRED"))
        self.assertTrue(result.new_order_allowed)

    def test_rejected_unlocks(self):
        result, _ = self.evaluate(lifecycle(final_status="REJECTED"))
        self.assertTrue(result.new_order_allowed)

    def test_terminal_partial_position_mismatch(self):
        result, _ = self.evaluate(lifecycle(
            final_status="CANCELED",
            final_filled_quantity=".4",
            final_remaining_quantity=".6",
            final_position_quantity=".2",
        ))
        self.assertTrue(result.safe_mode_engaged)
        self.assertFalse(result.new_order_allowed)

    def test_unknown_safe_mode(self):
        result, _ = self.evaluate(lifecycle(final_status="MYSTERY"))
        self.assertEqual(result.state, CompletionGateState.SAFE_MODE)
        self.assertFalse(result.new_order_allowed)

    def test_zero_write_counters(self):
        result, _ = self.evaluate(lifecycle())
        self.assertEqual(result.write_requests_executed, 0)
        self.assertEqual(result.actual_paper_orders_submitted, 0)
        self.assertEqual(result.live_orders_submitted, 0)

    def test_json(self):
        result, _ = self.evaluate(lifecycle())
        self.assertEqual(
            result.to_json_dict()["state"],
            "LOCKED_ACTIVE_ORDER",
        )


if __name__ == "__main__":
    unittest.main()
