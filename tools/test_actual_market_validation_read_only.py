from __future__ import annotations
import inspect, unittest
from actual_market_validation import service
class Tests(unittest.TestCase):
    def test_get_only(self):
        source = inspect.getsource(service)
        self.assertIn('method="GET"', source)
        self.assertNotIn('method="POST"', source)
        self.assertNotIn('method="DELETE"', source)
    def test_feature_records(self):
        bars = [{"c": 100+i, "v": 1000+i*10} for i in range(10)]
        raw = {"bars": {"bars": {"SPY": bars}}}
        records = service._records(raw, ["SPY"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["symbol"], "SPY")
    def test_no_bars(self):
        self.assertEqual(service._records({"bars":{"bars":{}}}, ["SPY"]), [])
    def test_read_only_flags_present(self):
        source = inspect.getsource(service.run_validation)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_order_submission_performed": False', source)
    def test_order_count_zero_present(self):
        source = inspect.getsource(service.run_validation)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
if __name__ == "__main__":
    unittest.main(verbosity=2)
