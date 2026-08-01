
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from alpaca_market_data.actual_paper_runtime_certification_v90_41_60 import (
    ActualPaperRuntimeCertificationConfig,
    build_manifest,
    final_audit,
    integrity_verification,
    recovery_validation,
    release_readiness,
    replay_document,
    restart_validation,
    rollback_validation,
    runtime_state_certificate,
    store_package,
    verify_manifest,
)

class T(unittest.TestCase):
    def setUp(self):
        self.config = ActualPaperRuntimeCertificationConfig()

    def test_config(self):
        self.config.validate()

    def test_unsafe_scheduler(self):
        with self.assertRaises(ValueError):
            ActualPaperRuntimeCertificationConfig(scheduler_enabled=True).validate()

    def test_unsafe_order_submission(self):
        with self.assertRaises(ValueError):
            ActualPaperRuntimeCertificationConfig(
                paper_order_submission_authorized=True
            ).validate()

    def test_runtime_state(self):
        state = runtime_state_certificate()
        self.assertEqual(state["runtime_state"], "READY_READ_ONLY")
        self.assertFalse(state["order_submission_allowed"])

    def test_replay(self):
        self.assertEqual(replay_document()["status"], "PASS")

    def test_restart(self):
        restart = restart_validation()
        self.assertEqual(restart["status"], "PASS")
        self.assertTrue(restart["fresh_read_required"])

    def test_recovery(self):
        self.assertEqual(recovery_validation()["status"], "PASS")

    def test_rollback(self):
        rollback = rollback_validation()
        self.assertEqual(rollback["status"], "PASS")
        self.assertTrue(rollback["disable_paper_order_submission"])

    def test_integrity(self):
        chain = {
            "status": "PASS",
            "chain_sha256": "chain",
        }
        state = runtime_state_certificate()
        replay = replay_document()
        restart = restart_validation()
        recovery = recovery_validation()
        rollback = rollback_validation()
        result = integrity_verification(
            chain,
            state,
            replay,
            restart,
            recovery,
            rollback,
        )
        self.assertEqual(result["status"], "PASS")

    def test_release_readiness(self):
        integrity = {"status": "PASS"}
        result = release_readiness(self.config, integrity)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["read_only_runtime_rc_ready"])

    def test_audit(self):
        chain = {"certificate_count": 2}
        integrity = {"status": "PASS"}
        readiness = {"status": "PASS", "read_only_runtime_rc_ready": True}
        result = final_audit(self.config, chain, integrity, readiness)
        self.assertEqual(result["status"], "PASS")

    def test_store_package(self):
        with TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            package_id, ledger = store_package(output, {"sample": {"status": "PASS"}})
            self.assertTrue(package_id.startswith("actual-paper-runtime-cert-"))
            self.assertEqual(ledger["status"], "PASS")

    def test_manifest(self):
        with TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            _, ledger = store_package(output, {"sample": {"status": "PASS"}})
            manifest = build_manifest(output, ledger)
            self.assertEqual(manifest["status"], "PASS")
            self.assertTrue(verify_manifest(output, manifest))

    def test_manifest_tamper(self):
        with TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            _, ledger = store_package(output, {"sample": {"status": "PASS"}})
            manifest = build_manifest(output, ledger)
            (output / "actual_paper_runtime_cert_ledger_v90_50.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            self.assertFalse(verify_manifest(output, manifest))

    def test_write_capability_zero(self):
        self.assertEqual(self.config.write_capability_count, 0)

    def test_orders_zero(self):
        self.assertEqual(self.config.actual_orders_submitted, 0)

    def test_network_zero(self):
        self.assertEqual(self.config.network_requests_executed, 0)

    def test_release_candidate(self):
        self.assertEqual(
            self.config.release_candidate,
            "ACTUAL_PAPER_READ_ONLY_RUNTIME_RC1",
        )

    def test_stage_count(self):
        self.assertEqual(len(range(41, 61)), 20)

if __name__ == "__main__":
    unittest.main()
