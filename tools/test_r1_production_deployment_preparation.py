from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from deployment.backup import write_restore_plan
from deployment.certificate import generate_release_certificate
from deployment.release_manifest import build_release_manifest
from deployment.retention import RetentionPolicy
from deployment.supervisor import build_supervisor_policy


class Tests(unittest.TestCase):
    def test_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "operations/test.py"
            path.parent.mkdir(parents=True)
            path.write_text("x = 1\n", encoding="utf-8")
            result = build_release_manifest(root)
        self.assertEqual(result["file_count"], 1)
        self.assertEqual(len(result["manifest_sha256"]), 64)

    def test_restore_is_manual(self):
        with tempfile.TemporaryDirectory() as directory:
            result = write_restore_plan(
                Path(directory) / "restore.json"
            )
        self.assertFalse(result["automatic_restore_enabled"])
        self.assertFalse(result["automatic_order_replay_enabled"])

    def test_supervisor_does_not_autostart(self):
        result = build_supervisor_policy()
        self.assertFalse(result["start_on_boot_enabled"])
        self.assertFalse(result["automatic_broker_restart_enabled"])

    def test_retention_policy(self):
        self.assertTrue(RetentionPolicy().evaluate()["valid"])

    def test_certificate_blocks_missing_actuals(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generate_release_certificate(Path(directory))
        self.assertFalse(result["eligible"])
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
