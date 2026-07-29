import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("finalize_release_v30_0.py")
SPEC = importlib.util.spec_from_file_location("finalize_release_v30_0", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class FinalizeReleaseV300Tests(unittest.TestCase):
    def make_project(self, root: Path) -> None:
        (root / "release/audit").mkdir(parents=True)
        (root / "release/certificates").mkdir(parents=True)
        (root / "release/manifest").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "src/app.py").write_text("print('ok')\n", encoding="utf-8")

        (root / "release/audit/production_readiness_audit_v29_7.json").write_text(
            json.dumps({
                "status": "PASS",
                "summary": {"pass": 11, "warn": 0, "fail": 0},
            }),
            encoding="utf-8",
        )
        (root / "release/certificates/FINAL_RELEASE_CERTIFICATE.json").write_text(
            json.dumps({
                "status": "PASS",
                "paper_trading_only": True,
            }),
            encoding="utf-8",
        )
        (root / "release/manifest/release_manifest.json").write_text(
            json.dumps({
                "version": "29.6",
                "paper_trading": True,
            }),
            encoding="utf-8",
        )

    def test_prerequisites_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            result = MOD.validate_prerequisites(root)
            self.assertEqual(result["status"], "PASS")

    def test_finalize_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            output = root / "dist/final.zip"

            with mock.patch.object(MOD, "git_commit", return_value="abc123"):
                with mock.patch.object(MOD, "git_branch", return_value="main"):
                    result = MOD.finalize(root, output)

            self.assertEqual(result["status"], "PASS")
            self.assertTrue(output.is_file())
            self.assertTrue((root / MOD.FINAL_MANIFEST).is_file())
            self.assertTrue((root / MOD.FINAL_CERTIFICATE).is_file())
            self.assertTrue((root / MOD.FINAL_NOTES).is_file())

            verify = MOD.verify_existing(root, output)
            self.assertEqual(verify["status"], "PASS")

            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn(MOD.FINAL_MANIFEST.as_posix(), names)
                self.assertIn(MOD.FINAL_CERTIFICATE.as_posix(), names)

    def test_prerequisite_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = MOD.finalize(Path(tmp), Path(tmp) / "final.zip")
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["stage"], "prerequisites")


if __name__ == "__main__":
    unittest.main(verbosity=2)
