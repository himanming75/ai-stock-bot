from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from runtime_deployment.deployment import RollbackPreview
from runtime_deployment.packaging import (
    BundleIntegrityVerifier,
    ReleaseBundleBuilder,
)
from runtime_deployment.service_control import (
    AutoRestartPolicyPreview,
    GracefulShutdownPreview,
    RuntimeServicePreview,
)


class Tests(unittest.TestCase):
    def test_service_preview_not_installed(self):
        result = RuntimeServicePreview().build(
            runtime_name="x",
            start_command="start",
            stop_command="stop",
        )
        self.assertFalse(result["service_install_performed"])
        self.assertFalse(result["service_start_performed"])

    def test_restart_disabled(self):
        result = AutoRestartPolicyPreview().create(
            maximum_restarts=3,
            window_minutes=30,
            delay_seconds=60,
        )
        self.assertFalse(result["automatic_restart_enabled"])

    def test_shutdown_preview_only(self):
        result = GracefulShutdownPreview().create(timeout_seconds=30)
        self.assertFalse(result["actual_shutdown_performed"])

    def test_rollback_preview_only(self):
        result = RollbackPreview().build(
            current_version="2",
            target_version="1",
        )
        self.assertFalse(result["actual_rollback_performed"])

    def test_bundle_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "a.txt"
            source.write_text("x", encoding="utf-8")
            bundle = root / "bundle.zip"
            result = ReleaseBundleBuilder().build_preview(
                root=root,
                output=bundle,
                files=[source],
            )
            verified = BundleIntegrityVerifier().verify(
                bundle_path=bundle,
                expected_sha256=result["bundle_sha256"],
            )
            self.assertTrue(verified["integrity_valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
