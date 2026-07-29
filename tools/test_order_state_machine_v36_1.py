import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "order_state_machine_v36_1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "order_state_machine_v36_1",
    MODULE_PATH,
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class OrderStateMachineV361Tests(unittest.TestCase):
    def build_accepted(self, quantity="10"):
        order = MOD.OrderLifecycle(
            symbol="AAPL",
            side="buy",
            quantity=quantity,
        )
        order.validate()
        order.route()
        order.accept()
        return order

    def test_happy_path_to_accepted(self):
        order = self.build_accepted()
        self.assertEqual(order.state, MOD.OrderState.ACCEPTED)
        self.assertEqual(order.snapshot().event_count, 4)

    def test_invalid_transition_is_rejected(self):
        order = MOD.OrderLifecycle(
            symbol="AAPL",
            side="buy",
            quantity="10",
        )
        with self.assertRaises(MOD.OrderLifecycleError):
            order.accept()

    def test_partial_fill(self):
        order = self.build_accepted()
        order.apply_fill("4", "200")
        snap = order.snapshot()
        self.assertEqual(snap.state, "partially_filled")
        self.assertEqual(snap.filled_quantity, "4")
        self.assertEqual(snap.remaining_quantity, "6")
        self.assertEqual(snap.average_fill_price, "200")

    def test_multiple_fills_reach_filled(self):
        order = self.build_accepted()
        order.apply_fill("4", "200")
        order.apply_fill("6", "210")
        snap = order.snapshot()
        self.assertEqual(snap.state, "filled")
        self.assertTrue(snap.terminal)
        self.assertEqual(snap.filled_quantity, "10")
        self.assertEqual(snap.average_fill_price, "206")

    def test_overfill_is_rejected(self):
        order = self.build_accepted()
        with self.assertRaises(MOD.OrderLifecycleError):
            order.apply_fill("11", "200")

    def test_cancel_workflow(self):
        order = self.build_accepted()
        order.request_cancel()
        order.confirm_cancel()
        snap = order.snapshot()
        self.assertEqual(snap.state, "canceled")
        self.assertTrue(snap.terminal)

    def test_fill_after_cancel_pending_can_complete(self):
        order = self.build_accepted()
        order.request_cancel()
        order.apply_fill("10", "200")
        self.assertEqual(order.state, MOD.OrderState.FILLED)

    def test_terminal_state_cannot_transition(self):
        order = self.build_accepted()
        order.apply_fill("10", "200")
        with self.assertRaises(MOD.OrderLifecycleError):
            order.request_cancel()

    def test_event_hashes_present(self):
        order = self.build_accepted()
        self.assertTrue(
            all(len(event.event_sha256) == 64 for event in order.timeline())
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
