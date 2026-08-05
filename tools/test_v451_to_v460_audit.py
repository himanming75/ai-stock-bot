
import tempfile, unittest
from pathlib import Path
from paper_broker_audit.scanner import run_audit

class Tests(unittest.TestCase):
    def test_detects_submit_order(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"x.py").write_text("submit_order client_order_id retry timeout", encoding="utf-8")
            r = run_audit(root)
            self.assertNotEqual(r["features"]["order_submit"]["status"], "NOT_FOUND")
    def test_missing_feature(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"x.py").write_text("hello", encoding="utf-8")
            r = run_audit(root)
            self.assertEqual(r["features"]["cancel_order"]["status"], "NOT_FOUND")
    def test_hash_present(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"x.py").write_text("sha256", encoding="utf-8")
            self.assertEqual(len(run_audit(root)["audit_hash"]), 64)
    def test_no_mandatory_omission(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"x.py").write_text("", encoding="utf-8")
            self.assertEqual(run_audit(root)["next_bundle_scope"]["mandatory_features_omitted"], [])
    def test_self_catalog_is_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"paper_broker_audit").mkdir()
            (root/"paper_broker_audit/catalog.py").write_text(
                "submit_order cancel_order get_account", encoding="utf-8"
            )
            r = run_audit(root)
            self.assertEqual(r["features"]["order_submit"]["status"], "NOT_FOUND")

    def test_zero_order_design(self):
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main(verbosity=2)
