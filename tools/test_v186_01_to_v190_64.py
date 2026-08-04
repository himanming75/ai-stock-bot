import tempfile,unittest
from pathlib import Path
from production_operations.config import load,validate
from production_operations.reporting import summarize_rows
from production_operations.health import evaluate as health
from production_operations.backup import create_snapshot,restore_plan
from production_operations.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t))
            self.assertFalse(c["broker_write_enabled"])
            self.assertFalse(c["live_submission_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_report_summary(self):
        r=summarize_rows([{"daily_return_pct":1,"total_pnl":10,"ending_equity":1010}])
        self.assertEqual(r["total_pnl"],10)
    def test_health_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(health(Path(t))["actual_live_orders_submitted"],0)
    def test_backup_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/"release/v140_final/actual").mkdir(parents=True)
            (root/"release/v140_final/actual/x.json").write_text("{}")
            b=create_snapshot(root)
            self.assertGreaterEqual(b["file_count"],1)
    def test_restore_not_automatic(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(restore_plan(Path(t))["automatic_restore_performed"])
    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t),create_backup=False)["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
