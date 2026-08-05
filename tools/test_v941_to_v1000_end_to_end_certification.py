from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from paper_platform_certification.checks import detect_bar_sort_hotfix
from paper_platform_certification.service import PaperPlatformCertificationService

class Tests(unittest.TestCase):
    def test_hotfix_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "service.py"
            path.write_text(
                'x={"sort": "desc"}\nreturn sorted([], key=lambda x: x)\n',
                encoding="utf-8",
            )
            self.assertEqual(detect_bar_sort_hotfix(path)["status"], "PASS")

    def test_missing_component_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = PaperPlatformCertificationService().evaluate(
                root=root,
                output_dir=root / "out",
            )
            self.assertEqual(result["status"], "BLOCKED")

    def test_outputs_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            PaperPlatformCertificationService().evaluate(
                root=root,
                output_dir=root / "out",
            )
            self.assertTrue((root / "out/paper_platform_certificate.json").exists())
            self.assertTrue((root / "out/certification_ledger.jsonl").exists())

    def test_market_validation_is_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = PaperPlatformCertificationService().evaluate(
                root=root,
                output_dir=root / "out",
            )
            self.assertEqual(
                result["market_open_validation"]["status"],
                "PENDING_MARKET_VALIDATION",
            )

    def test_zero_order_contract(self):
        source = inspect.getsource(PaperPlatformCertificationService)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
