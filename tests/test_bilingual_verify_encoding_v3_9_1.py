
from pathlib import Path
import unittest


class Tests(unittest.TestCase):
    def test_powershell_verifier_is_ascii_only(self):
        raw = Path(
            "VERIFY_V3_9_1.ps1"
        ).read_bytes()

        self.assertTrue(
            all(byte < 128 for byte in raw)
        )

    def test_python_helper_contains_korean_labels(self):
        text = Path(
            "dashboard/verify_bilingual_utf8_v3_9_1.py"
        ).read_text(
            encoding="utf-8"
        )

        for label in (
            "시스템 상태",
            "계좌 평가금액",
            "현재 보유 포지션",
            "일별 실현손익",
            "누적 성과 및 거래 분석",
        ):
            self.assertIn(
                label,
                text,
            )

    def test_existing_v39_html_patch_present(self):
        text = Path(
            "dashboard/templates/operations_dashboard_v3_2.html"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "시스템 상태",
            text,
        )
        self.assertIn(
            "누적 성과 및 거래 분석",
            text,
        )

    def test_existing_v39_server_patch_present(self):
        text = Path(
            "dashboard/operations_dashboard_v3_2.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "V3.9_CANONICAL_PERFORMANCE_UNIFICATION",
            text,
        )

    def test_read_only(self):
        text = Path(
            "dashboard/verify_bilingual_utf8_v3_9_1.py"
        ).read_text(
            encoding="utf-8"
        )

        for bad in (
            "TradingClient(",
            "submit_order(",
            "MarketOrderRequest(",
        ):
            self.assertNotIn(
                bad,
                text,
            )


if __name__ == "__main__":
    unittest.main()
