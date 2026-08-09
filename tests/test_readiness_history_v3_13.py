
from datetime import datetime, timezone, timedelta
from pathlib import Path
import importlib.util
import tempfile
import unittest

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load(Path("dashboard/readiness_history_v3_13.py"), "v313_history")
        cls.analytics = Path("dashboard/trade_analytics_v3_5.py").read_text(encoding="utf-8")
        cls.html = Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def readiness(self, count=2, score=49.0, status="NOT_READY"):
        return {
            "status": status,
            "overall_score": score,
            "raw_overall_score": score,
            "canonical_numeric_trade_count": count,
            "scores": {
                "sample_confidence": 10,
                "profitability_quality": 100,
                "risk_quality": 100,
                "consistency": 90,
                "diversification": 33,
            },
            "blockers": ["sample"],
        }

    def test_dedup_same_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
            a = self.m.record_if_changed(root, self.readiness(), now)
            b = self.m.record_if_changed(root, self.readiness(), now + timedelta(minutes=1))
            self.assertTrue(a["written"])
            self.assertFalse(b["written"])

    def test_changed_trade_count_writes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
            self.m.record_if_changed(root, self.readiness(count=2), now)
            b = self.m.record_if_changed(root, self.readiness(count=3), now + timedelta(minutes=1))
            self.assertTrue(b["written"])

    def test_api_exposed(self):
        self.assertIn('"readiness_history": readiness_history', self.analytics)

    def test_ui_present(self):
        self.assertIn('id="readinessHistorySection"', self.html)
        self.assertIn("Readiness History & Evidence Trend / 준비도 이력 및 증거 추세", self.html)

    def test_safety_contract(self):
        with tempfile.TemporaryDirectory() as td:
            summary = self.m.build_history_summary(Path(td), self.readiness())
            self.assertTrue(summary["contracts"]["analytics_history_write_only"])
            self.assertFalse(summary["contracts"]["broker_write_performed"])
            self.assertFalse(summary["contracts"]["paper_runtime_modified"])

if __name__ == "__main__":
    unittest.main()
