import tempfile,unittest,json
from pathlib import Path
from final_production_release.config import load,validate
from final_production_release.inventory import build
from final_production_release.integration import evaluate as integration
from final_production_release.integrity import build as integrity
from final_production_release.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t))
            self.assertFalse(c["automatic_order_submission_enabled"])
            self.assertFalse(c["broker_write_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_inventory_live_zero_empty(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(build(Path(t))["total_actual_live_orders_submitted"],0)
    def test_inventory_detects_live_order(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/"release/v120_final/actual";p.mkdir(parents=True)
            (p/"v120_final_release_result.json").write_text(json.dumps({"actual_live_orders_submitted":1}))
            self.assertEqual(build(root)["total_actual_live_orders_submitted"],1)
    def test_integration_reports_missing(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(integration(Path(t))["all_modules_present"])
    def test_integrity_reports_missing(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(integrity(Path(t))["all_present"])
    def test_engine_never_enables_live(self):
        with tempfile.TemporaryDirectory() as t:
            r=evaluate(Path(t),create_release_bundle=False)
            self.assertFalse(r["live_trading_ready"])
            self.assertFalse(r["broker_write_enabled"])
    def test_engine_live_zero_empty(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t),False)["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
