import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_release_v29_6.py")
SPEC = importlib.util.spec_from_file_location("build_release_v29_6", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class BuildReleaseV296Tests(unittest.TestCase):
    def make_project(self, root: Path) -> None:
        (root / "backtest").mkdir()
        (root / "release/manifest").mkdir(parents=True)
        (root / "release/artifacts").mkdir(parents=True)
        (root / "release/reports").mkdir(parents=True)
        (root / "release/certificates").mkdir(parents=True)
        (root / "backtest/example.py").write_text("print('ok')\n", encoding="utf-8")
        (root / "README.md").write_text("# Test\n", encoding="utf-8")
        (root / "release/manifest/release_manifest.json").write_text(
            json.dumps({
                "version": "29.6",
                "release_name": "Test Release",
                "paper_trading": True,
                "audit": "PASS",
            }),
            encoding="utf-8",
        )

    def test_build_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            zip_path = root / "dist/release.zip"

            result = MOD.build_release(root, zip_path)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(zip_path.is_file())
            self.assertTrue((root / "release/manifest/sha256_manifest.json").is_file())
            self.assertTrue((root / "release/certificates/FINAL_RELEASE_CERTIFICATE.json").is_file())

            verify = MOD.verify_release(root, zip_path)
            self.assertEqual(verify["status"], "PASS")

            with zipfile.ZipFile(zip_path) as archive:
                names = set(archive.namelist())
                self.assertIn("release/manifest/release_manifest.json", names)
                self.assertIn("release/manifest/sha256_manifest.json", names)
                self.assertIn("release/certificates/FINAL_RELEASE_CERTIFICATE.json", names)

    def test_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            zip_path = root / "dist/release.zip"
            MOD.build_release(root, zip_path)

            (root / "README.md").write_text("# Tampered\n", encoding="utf-8")
            verify = MOD.verify_release(root, zip_path)
            self.assertEqual(verify["status"], "FAIL")
            self.assertTrue(any("README.md" in error for error in verify["errors"]))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
