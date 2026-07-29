import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("html_tear_sheet_final_report_v29_5b.py")
SPEC = importlib.util.spec_from_file_location("v29_5b_report", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class Tests(unittest.TestCase):
    def test_missing_sections(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.html"
            MOD.generate_report({"title": "Minimal"}, p)
            self.assertIn(
                "No summary metrics available",
                p.read_text(encoding="utf-8"),
            )

    def test_self_contained_html(self):
        payload = {
            "title": "Test",
            "summary_metrics": {"total_return": 0.1},
            "equity_curve": [
                {"date": "2026-01-01", "equity": 100},
                {"date": "2026-01-02", "equity": 110},
            ],
        }
        data = MOD.normalize_payload(payload)
        rendered = MOD.render_html(data)
        self.assertIn("<!doctype html>", rendered.lower())
        self.assertIn("<svg", rendered)
        self.assertNotIn("https://", rendered)
        self.assertNotIn("<script", rendered.lower())

    def test_normalize_auto_drawdown(self):
        payload = {
            "title": "Test",
            "equity_curve": [
                {"date": "2026-01-01", "equity": 100},
                {"date": "2026-01-02", "equity": 110},
                {"date": "2026-01-03", "equity": 99},
            ],
        }
        data = MOD.normalize_payload(payload)
        self.assertEqual(len(data.drawdown_points), 3)
        self.assertAlmostEqual(data.drawdown_points[-1][1], -0.1)

    def test_cli_and_manifest(self):
        payload = {
            "title": "CLI Test",
            "summary_metrics": {"total_return": 0.05},
            "equity_curve": [
                {"date": "2026-01-01", "equity": 100},
                {"date": "2026-01-02", "equity": 105},
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            source = d / "input.json"
            report = d / "report.html"
            manifest = d / "manifest.json"
            source.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--input", str(source),
                    "--output", str(report),
                    "--manifest-output", str(manifest),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(report.exists())
            self.assertTrue(manifest.exists())

            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "PASS")
            self.assertEqual(
                data["html_sha256"],
                hashlib.sha256(report.read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
