from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from final_operations.release_manifest import (
    build_release_manifest,
)


class Tests(unittest.TestCase):
    def test_manifest_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "final_operations"
            package.mkdir()
            (package / "x.py").write_text("x=1\n", encoding="utf-8")
            result = build_release_manifest(root)
        self.assertEqual(result["tracked_file_count"], 1)
        self.assertEqual(len(result["manifest_sha256"]), 64)

    def test_manifest_does_not_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = build_release_manifest(root)
        self.assertFalse(result["actual_release_performed"])

    def test_manifest_excludes_pycache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "final_operations/__pycache__"
            cache.mkdir(parents=True)
            (cache / "x.pyc").write_bytes(b"x")
            result = build_release_manifest(root)
        self.assertEqual(result["tracked_file_count"], 0)

    def test_hash_changes_with_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "final_operations"
            package.mkdir()
            path = package / "x.py"
            path.write_text("x=1\n", encoding="utf-8")
            first = build_release_manifest(root)["manifest_sha256"]
            path.write_text("x=2\n", encoding="utf-8")
            second = build_release_manifest(root)["manifest_sha256"]
        self.assertNotEqual(first, second)

    def test_empty_manifest_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            result = build_release_manifest(Path(directory))
        self.assertEqual(result["tracked_file_count"], 0)
        self.assertEqual(len(result["manifest_sha256"]), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
