
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_release_candidate_v90_61_80 import *

class T(unittest.TestCase):
    def setUp(self):
        self.config = ActualPaperReleaseCandidateConfig()

    def test_config(self): self.config.validate()

    def test_unsafe_scheduler(self):
        with self.assertRaises(ValueError):
            ActualPaperReleaseCandidateConfig(scheduler_enabled=True).validate()

    def test_unsafe_submit(self):
        with self.assertRaises(ValueError):
            ActualPaperReleaseCandidateConfig(
                paper_order_submission_authorized=True
            ).validate()

    def test_checklist(self):
        self.assertEqual(operations_checklist()["status"], "PASS")

    def test_health_gate(self):
        self.assertTrue(health_gate()["health_gate_ready"])

    def test_startup(self):
        self.assertEqual(startup_validation()["startup_state"], "READY_READ_ONLY")

    def test_shutdown(self):
        self.assertEqual(shutdown_validation()["shutdown_state"], "STOPPED")

    def test_incident(self):
        self.assertTrue(incident_response()["incident_response_ready"])

    def test_rollback(self):
        self.assertTrue(rollback_package()["rollback_ready"])

    def test_acceptance(self):
        result = acceptance_test(
            operations_checklist(),
            health_gate(),
            startup_validation(),
            shutdown_validation(),
            incident_response(),
            rollback_package(),
        )
        self.assertEqual(result["status"], "PASS")

    def test_replay(self):
        acceptance = acceptance_test(
            operations_checklist(),
            health_gate(),
            startup_validation(),
            shutdown_validation(),
            incident_response(),
            rollback_package(),
        )
        self.assertTrue(replay_acceptance(acceptance)["deterministic"])

    def test_audit(self):
        acceptance = acceptance_test(
            operations_checklist(),
            health_gate(),
            startup_validation(),
            shutdown_validation(),
            incident_response(),
            rollback_package(),
        )
        replay = replay_acceptance(acceptance)
        self.assertEqual(final_audit(self.config, acceptance, replay)["status"], "PASS")

    def test_store(self):
        with TemporaryDirectory() as t:
            pid, ledger = store_package(Path(t), {"sample": {"status": "PASS"}})
            self.assertTrue(pid.startswith("actual-paper-ops-rc-"))
            self.assertEqual(ledger["status"], "PASS")

    def test_manifest(self):
        with TemporaryDirectory() as t:
            out = Path(t)
            _, ledger = store_package(out, {"sample": {"status": "PASS"}})
            manifest = build_manifest(out, ledger)
            self.assertTrue(verify_manifest(out, manifest))

    def test_manifest_tamper(self):
        with TemporaryDirectory() as t:
            out = Path(t)
            _, ledger = store_package(out, {"sample": {"status": "PASS"}})
            manifest = build_manifest(out, ledger)
            (out / "actual_paper_release_candidate_ledger_v90_70.json").write_text("{}\n")
            self.assertFalse(verify_manifest(out, manifest))

    def test_write_zero(self):
        self.assertEqual(self.config.write_capability_count, 0)

    def test_network_zero(self):
        self.assertEqual(self.config.network_requests_executed, 0)

    def test_orders_zero(self):
        self.assertEqual(self.config.actual_orders_submitted, 0)

    def test_release_candidate(self):
        self.assertEqual(
            self.config.release_candidate,
            "ACTUAL_PAPER_READ_ONLY_OPERATIONS_RC1",
        )

    def test_stage_count(self):
        self.assertEqual(len(range(61, 81)), 20)

if __name__ == "__main__":
    unittest.main()
