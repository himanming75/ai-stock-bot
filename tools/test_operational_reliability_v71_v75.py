import tempfile
import unittest
from pathlib import Path

from operational_reliability_v71_v75 import OperationalReliabilityPack


class Tests(unittest.TestCase):
    def test_lock_audit_no_delete(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = OperationalReliabilityPack(root)
            r = svc.v72_session_lock_recovery_audit()
            self.assertFalse(r["automatic_lock_deletion"])
            self.assertFalse(r["automatic_recovery_performed"])

    def test_consistency_empty_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = OperationalReliabilityPack(root)
            r = svc.v73_runtime_ledger_consistency()
            self.assertEqual(r["malformed_total"], 0)

    def test_resource_monitor(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = OperationalReliabilityPack(root)
            r = svc.v74_system_resource_monitor()
            self.assertGreater(r["disk_total_bytes"], 0)

    def test_health_report_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = OperationalReliabilityPack(root)
            r = svc.v75_operational_health_report()
            self.assertFalse(r["broker_write_performed"])

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = OperationalReliabilityPack(root)
            r = svc.run()
            self.assertEqual(r["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = OperationalReliabilityPack(root)
            svc.run()
            self.assertTrue(
                (
                    root
                    / "runtime/operational_reliability_v71_v75/"
                      "latest_operational_reliability_report.json"
                ).exists()
            )

    def test_no_automatic_repair(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = OperationalReliabilityPack(root)
            r = svc.v75_operational_health_report()
            self.assertFalse(r["automatic_repair_performed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
