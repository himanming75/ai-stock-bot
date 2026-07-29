import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("release_integrity_audit_v30_1.py")
SPEC = importlib.util.spec_from_file_location("release_integrity_audit_v30_1", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class ReleaseIntegrityAuditV301Tests(unittest.TestCase):
    def test_result_factory(self):
        item = MOD.result("x", "Example", True, "ok", "bad")
        self.assertEqual(item.status, "PASS")
        self.assertEqual(item.summary, "ok")

    def test_render_html(self):
        report = {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "status": "PASS",
            "summary": {"pass": 1, "fail": 0},
            "checks": [{
                "check_id": "x",
                "title": "Example",
                "status": "PASS",
                "summary": "Everything passed",
                "details": {"value": True},
            }],
        }
        rendered = MOD.render_html(report)
        self.assertIn("<!doctype html>", rendered.lower())
        self.assertIn("Release Integrity Audit", rendered)
        self.assertIn("Everything passed", rendered)

    def test_missing_zip_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checks = MOD.audit_zip(root, root / "missing.zip")
            self.assertEqual(checks[0].status, "FAIL")

    def test_main_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_path = root / "audit.json"
            html_path = root / "audit.html"
            fake = {
                "schema_version": "test",
                "version": "30.1",
                "audited_release": "30.0.0",
                "expected_tag": "v30.0.0",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "status": "PASS",
                "summary": {"pass": 1, "fail": 0},
                "checks": [],
            }
            with mock.patch.object(MOD, "run_audit", return_value=fake):
                code = MOD.main([
                    "--root", str(root),
                    "--zip", str(root / "missing.zip"),
                    "--json-output", str(json_path),
                    "--html-output", str(html_path),
                ])
            self.assertEqual(code, 0)
            self.assertTrue(json_path.is_file())
            self.assertTrue(html_path.is_file())
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
