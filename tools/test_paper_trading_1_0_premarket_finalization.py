from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from paper_completion_audit.scanner import RepositoryScanner
from paper_completion_audit.planner import build_plan


class Tests(unittest.TestCase):
    def _fixture(self, root: Path) -> None:
        samples = {
            "deployment/credential_vault.py": "paper_only = True\nlive_submission_enabled = False\n",
            "actual_market_polling/service.py": "def poll_market(): pass\n",
            "ai_strategy/signal.py": "def generate_signal(): pass\n",
            "risk_manager/guardrail.py": "broker_write_enabled = False\n",
            "broker_integration/paper_execution.py": "paper_only = True\ndef submit_order(): pass\n",
            "order_lifecycle/reconciliation.py": "def reconcile_fill(): pass\n",
            "portfolio/position_manager.py": "def sync_positions(): pass\n",
            "paper_automation_controller/controller.py": "def run_session(): pass\n",
            "automation_watchdog/recovery.py": "def recover_checkpoint(): pass\n",
            "paper_runtime/end_of_day.py": "def end_of_day(): pass\n",
            "web_controller/operations_api.py": "def dashboard(): pass\n",
            "actual_validation/paper_completion.py": "def paper_completion(): pass\n",
        }
        for relative, content in samples.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_all_categories_found(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root)
            audit = RepositoryScanner(root).scan()
            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["missing_categories"], [])

    def test_plan_scope_locked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root)
            plan = build_plan(RepositoryScanner(root).scan())
            self.assertTrue(plan["scope_locked"])
            self.assertFalse(plan["new_feature_development_allowed"])
            self.assertTrue(plan["tomorrow_actual_validation_excluded_today"])

    def test_missing_category_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "only_signal.py").write_text(
                "def generate_signal(): pass",
                encoding="utf-8",
            )
            audit = RepositoryScanner(root).scan()
            self.assertEqual(audit["status"], "BLOCKED")
            self.assertGreater(len(audit["missing_categories"]), 0)

    def test_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root)
            a = root / "duplicate_a.py"
            b = root / "duplicate_b.py"
            content = "def paper_completion(): pass\n"
            a.write_text(content, encoding="utf-8")
            b.write_text(content, encoding="utf-8")
            audit = RepositoryScanner(root).scan()
            self.assertTrue(any(
                len(group["paths"]) >= 2
                for group in audit["exact_duplicate_groups"]
            ))

    def test_write_capable_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root)
            audit = RepositoryScanner(root).scan()
            self.assertTrue(any(
                item["safety_flags"]["contains_submit_order"]
                for item in audit["write_capable_files"]
            ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
