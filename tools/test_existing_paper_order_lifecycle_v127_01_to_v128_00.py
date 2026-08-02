from dataclasses import dataclass
from decimal import Decimal
import unittest

from autonomous_paper_runtime.order_lifecycle import (
    ExistingPaperOrderLifecycleTracker, LifecycleClass
)

@dataclass
class Order:
    order_id: str = "broker-1"
    client_order_id: str = "single-legacy"
    symbol: str = "AAPL"
    side: str = "buy"
    quantity: Decimal = Decimal("1")
    filled_quantity: Decimal = Decimal("0")
    status: str = "accepted"

class T(unittest.TestCase):
    def setUp(self): self.tracker = ExistingPaperOrderLifecycleTracker()

    def test_accepted_active(self):
        r=self.tracker.track(Order()); self.assertEqual(r.lifecycle_class,LifecycleClass.ACTIVE); self.assertFalse(r.new_order_allowed)
    def test_new_active(self):
        self.assertFalse(self.tracker.track(Order(status="new")).terminal)
    def test_partial(self):
        r=self.tracker.track(Order(status="partially_filled",filled_quantity=Decimal(".4"))); self.assertEqual(r.remaining_quantity,"0.6"); self.assertEqual(r.lifecycle_class,LifecycleClass.PARTIAL)
    def test_filled(self):
        r=self.tracker.track(Order(status="filled",filled_quantity=Decimal("1"))); self.assertTrue(r.terminal); self.assertTrue(r.new_order_allowed)
    def test_canceled(self):
        self.assertTrue(self.tracker.track(Order(status="canceled")).terminal)
    def test_rejected(self):
        self.assertEqual(self.tracker.track(Order(status="rejected")).lifecycle_class,LifecycleClass.TERMINAL_NO_FILL)
    def test_expired(self):
        self.assertTrue(self.tracker.track(Order(status="expired")).new_order_allowed)
    def test_unknown_safe_mode(self):
        r=self.tracker.track(Order(status="mystery")); self.assertTrue(r.safe_mode_engaged); self.assertFalse(r.new_order_allowed)
    def test_fill_ratio(self):
        self.assertEqual(self.tracker.track(Order(quantity=Decimal("2"),filled_quantity=Decimal("1"),status="partially_filled")).fill_ratio,"0.5")
    def test_zero_qty(self):
        self.assertEqual(self.tracker.track(Order(quantity=Decimal("0"))).fill_ratio,"0")
    def test_zero_writes(self):
        r=self.tracker.track(Order(),network_requests_executed=1); self.assertEqual(r.network_requests_executed,1); self.assertEqual(r.write_requests_executed,0); self.assertEqual(r.actual_paper_orders_submitted,0); self.assertEqual(r.live_orders_submitted,0)
    def test_json(self):
        self.assertEqual(self.tracker.track(Order()).to_json_dict()["lifecycle_class"],"ACTIVE")

if __name__=="__main__": unittest.main()
