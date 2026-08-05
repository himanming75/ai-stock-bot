from __future__ import annotations
import inspect
import unittest
from decimal import Decimal
from actual_market_polling import service

class Tests(unittest.TestCase):
    def bars(self):
        return [{"c": 100+i, "v": 1000+i*10, "t": f"T{i}"} for i in range(10)]

    def test_record_requires_six_bars(self):
        self.assertIsNone(service.build_record("SPY", self.bars()[:5], []))

    def test_record_created(self):
        returns=[]
        record=service.build_record("SPY", self.bars(), returns)
        self.assertEqual(record["symbol"], "SPY")
        self.assertEqual(len(returns), 1)

    def test_finalize_records(self):
        returns=[]
        record=service.build_record("SPY", self.bars(), returns)
        result=service.finalize_records([record], returns)
        self.assertEqual(result[0]["breadth_score"], "1")

    def test_get_only_contract(self):
        source=inspect.getsource(service.ReadOnlyAlpaca)
        self.assertIn('method="GET"', source)
        self.assertNotIn('method="POST"', source)
        self.assertNotIn('method="DELETE"', source)

    def test_zero_order_contract(self):
        source=inspect.getsource(service.ActualMarketPollingValidationService)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
