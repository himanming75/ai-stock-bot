from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from deployment.config_audit import audit_configuration


class Tests(unittest.TestCase):
    def test_venv_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "deployment" / "x.py"
            source.parent.mkdir(parents=True)
            source.write_text("safe = True\n", encoding="utf-8")

            venv_file = root / ".venv" / "Lib" / "site-packages" / "huge.py"
            venv_file.parent.mkdir(parents=True)
            venv_file.write_text("ignored = True\n", encoding="utf-8")

            result = audit_configuration(root)

        self.assertTrue(result["valid"])
        self.assertEqual(result["scanned_file_count"], 1)

    def test_cache_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "operations" / "x.py"
            source.parent.mkdir(parents=True)
            source.write_text("safe = True\n", encoding="utf-8")

            cache = root / "__pycache__" / "x.py"
            cache.parent.mkdir(parents=True)
            cache.write_text("ignored = True\n", encoding="utf-8")

            result = audit_configuration(root)

        self.assertEqual(result["scanned_file_count"], 1)

    def test_large_text_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "operations" / "x.py"
            source.parent.mkdir(parents=True)
            source.write_text("safe = True\n", encoding="utf-8")

            large = root / "release" / "large.txt"
            large.parent.mkdir(parents=True)
            with large.open("wb") as handle:
                handle.truncate(11 * 1024 * 1024)

            result = audit_configuration(root)

        self.assertEqual(result["scanned_file_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
