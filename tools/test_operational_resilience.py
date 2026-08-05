from __future__ import annotations
from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path

from operational_resilience.configuration import ConfigurationSchemaValidator
from operational_resilience.faults import FaultInjectionSimulator
from operational_resilience.snapshots import StateSnapshotManager
from operational_resilience.retention import DataRetentionPlanner


class Tests(unittest.TestCase):
    def test_live_config_rejected(self):
        result = ConfigurationSchemaValidator().validate({
            "schema_version": 1,
            "environment": "prod",
            "broker_mode": "live",
            "network_enabled": False,
            "write_enabled": False,
            "automatic_order_submission_enabled": False,
        })
        self.assertFalse(result["valid"])

    def test_snapshot_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = StateSnapshotManager()
            snapshot = manager.create(
                output=Path(directory) / "snapshot.json",
                state={"x": 1},
                source_name="fixture",
            )
            self.assertTrue(manager.verify(snapshot)["integrity_valid"])

    def test_fault_simulation_not_live(self):
        result = FaultInjectionSimulator().simulate("WORKER_FAILURE")
        self.assertFalse(result["fault_injected_into_live_runtime"])

    def test_unknown_fault_rejected(self):
        with self.assertRaises(ValueError):
            FaultInjectionSimulator().simulate("UNKNOWN")

    def test_retention_preview_only(self):
        now = datetime.now(timezone.utc)
        result = DataRetentionPlanner().plan(
            records=[{"created_at": now.isoformat()}],
            retain_days=30,
            observed_at=now,
        )
        self.assertFalse(result["actual_files_deleted"])
        self.assertFalse(result["actual_files_archived"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
