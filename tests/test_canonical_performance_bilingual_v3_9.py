
from pathlib import Path
import unittest


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = Path(
            "dashboard/operations_dashboard_v3_2.py"
        ).read_text(encoding="utf-8")
        cls.html = Path(
            "dashboard/templates/operations_dashboard_v3_2.html"
        ).read_text(encoding="utf-8")

    def test_canonical_performance_marker(self):
        self.assertIn(
            "V3.9_CANONICAL_PERFORMANCE_UNIFICATION",
            self.server,
        )

    def test_performance_overridden_from_analytics(self):
        self.assertIn(
            'analytics_historical.get("net_realized_pnl")',
            self.server,
        )
        self.assertIn(
            '"canonical_source": True',
            self.server,
        )

    def test_daily_pnl_uses_canonical_analytics(self):
        self.assertIn(
            'payload["trade_analytics"].get("daily")',
            self.server,
        )
        self.assertIn(
            'payload["visualization"]["daily_realized_pnl"]',
            self.server,
        )

    def test_bilingual_core_labels(self):
        required = (
            "System Health / 시스템 상태",
            "Account Equity / 계좌 평가금액",
            "Current Positions / 현재 보유 포지션",
            "Performance / 성과",
            "Win Rate / 승률",
            "Daily Realized P/L / 일별 실현손익",
            "Historical Performance & Trade Analytics / 누적 성과 및 거래 분석",
        )
        for value in required:
            self.assertIn(value, self.html)

    def test_read_only(self):
        combined = self.server + self.html
        for bad in (
            "TradingClient(",
            "submit_order(",
            "MarketOrderRequest(",
        ):
            self.assertNotIn(bad, combined)


if __name__ == "__main__":
    unittest.main()
