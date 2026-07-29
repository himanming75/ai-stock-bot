import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("production_readiness_audit_v29_7.py")
SPEC = importlib.util.spec_from_file_location("production_readiness_audit_v29_7", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class ProductionReadinessAuditV297Tests(unittest.TestCase):
    def test_check_factory(self):
        result = MOD.check("x", "Example", True, "pass", "fail")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.summary, "pass")

    def test_render_html(self):
        report = {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "status": "PASS",
            "summary": {"pass": 1, "warn": 0, "fail": 0},
            "checks": [{
                "check_id": "x",
                "title": "Example",
                "status": "PASS",
                "summary": "All good",
                "details": {"value": True},
            }],
        }
        rendered = MOD.render_html(report)
        self.assertIn("<!doctype html>", rendered.lower())
        self.assertIn("Production Readiness Audit", rendered)
        self.assertIn("All good", rendered)

    def test_required_files_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = MOD.audit_required_files(Path(tmp))
            self.assertEqual(result.status, "FAIL")
            self.assertTrue(result.details["missing"])

    def test_main_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_out = root / "audit.json"
            html_out = root / "audit.html"
            fake = {
                "schema_version": "test",
                "version": "29.7",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "status": "PASS",
                "summary": {"pass": 1, "warn": 0, "fail": 0},
                "checks": [],
            }
            with mock.patch.object(MOD, "run_audit", return_value=fake):
                code = MOD.main([
                    "--root", str(root),
                    "--json-output", str(json_out),
                    "--html-output", str(html_out),
                ])
            self.assertEqual(code, 0)
            self.assertTrue(json_out.is_file())
            self.assertTrue(html_out.is_file())
            data = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
