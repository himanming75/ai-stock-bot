from __future__ import annotations
import inspect, tempfile, unittest
from pathlib import Path

from ai_engine_final_certification.checks import COMPONENTS
from ai_engine_final_certification.io import write_json
from ai_engine_final_certification.service import AIEngineFinalCertificationService

class Tests(unittest.TestCase):
    def populate(self, root: Path, technical_status="BLOCKED", unified_status="PARTIAL_INPUT"):
        for spec in COMPONENTS:
            path = root / spec["path"]
            status = "PASS"
            if spec["name"] == "MARKET_INTELLIGENCE_FEATURE_STORE":
                status = technical_status
            elif spec["name"] == "MULTI_STRATEGY_ENSEMBLE":
                status = technical_status
            elif spec["name"] == "UNIFIED_AI_DECISION":
                status = unified_status
            write_json(path, {
                "status": status,
                "input_mode": "OFFLINE_FIXTURE_OR_USER_SUPPLIED_JSON" if spec["fixture_capable"] else "",
                "actual_broker_write_performed": False,
                "actual_order_submission_performed": False,
                "actual_paper_orders_submitted": 0,
                "actual_live_orders_submitted": 0,
            })

    def test_conditional_certificate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.populate(root)
            result = AIEngineFinalCertificationService().evaluate(
                repository_root=root, output_dir=root / "out"
            )
            self.assertEqual(result["status"], "PASS")
            self.assertIn("CONDITIONALLY_CERTIFIED", result["certificate_status"])

    def test_full_certificate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.populate(root, "PASS", "PASS")
            result = AIEngineFinalCertificationService().evaluate(
                repository_root=root, output_dir=root / "out"
            )
            self.assertEqual(result["certificate_status"], "FULLY_CERTIFIED")

    def test_missing_files_block(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = AIEngineFinalCertificationService().evaluate(
                repository_root=root, output_dir=root / "out"
            )
            self.assertEqual(result["status"], "BLOCKED")

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.populate(root)
            AIEngineFinalCertificationService().evaluate(
                repository_root=root, output_dir=root / "out"
            )
            self.assertTrue((root / "out/ai_engine_certificate.json").exists())
            self.assertTrue((root / "out/ai_engine_certification_ledger.jsonl").exists())

    def test_zero_order_contract(self):
        source = inspect.getsource(AIEngineFinalCertificationService)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
