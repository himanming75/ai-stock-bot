
from pathlib import Path
import unittest


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analytics = Path(
            "dashboard/trade_analytics_v3_5.py"
        ).read_text(encoding="utf-8")
        cls.html = Path(
            "dashboard/templates/operations_dashboard_v3_2.html"
        ).read_text(encoding="utf-8")

    def test_trade_detail_api(self):
        self.assertIn(
            '"trade_details": list(reversed(numeric[-500:]))',
            self.analytics,
        )

    def test_trade_detail_section(self):
        self.assertIn('id="tradeDetailSection"', self.html)
        self.assertIn(
            "Canonical Trade Detail & Lifecycle Matrix / 정식 거래 상세 및 라이프사이클",
            self.html,
        )

    def test_filters(self):
        for value in (
            'id="tradeFilterDate"',
            'id="tradeFilterSymbol"',
            'id="tradeFilterReason"',
            'id="tradeFilterResult"',
        ):
            self.assertIn(value, self.html)

    def test_detail_columns(self):
        for value in (
            "Entry Time / 진입시간",
            "Exit Time / 청산시간",
            "Holding / 보유시간",
            "Entry Price / 진입가",
            "Exit Price / 청산가",
            "Realized P/L / 실현손익",
            "Return / 수익률",
            "Order ID / 주문 ID",
        ):
            self.assertIn(value, self.html)

    def test_read_only(self):
        combined = self.analytics + self.html
        for bad in (
            "TradingClient(",
            "submit_order(",
            "MarketOrderRequest(",
        ):
            self.assertNotIn(bad, combined)


if __name__ == "__main__":
    unittest.main()
