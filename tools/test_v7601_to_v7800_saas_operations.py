from __future__ import annotations
import sqlite3
import tempfile
import unittest
from pathlib import Path

from saas_operations.backup import BackupManager
from saas_operations.health import HeartbeatRegistry
from saas_operations.metrics import MetricsRegistry
from saas_operations.notifications import (
    MockNotificationAdapter,
    NotificationQueue,
)
from saas_operations.service import (
    SaaSOperationsCertificationService,
)
from saas_operations.service_manager import (
    SafeServiceManager,
)


class Tests(unittest.TestCase):
    def test_metrics(self):
        metrics = MetricsRegistry()
        metrics.record_request(
            route="/health",
            latency_ms=10,
            status_code=200,
        )
        metrics.record_request(
            route="/missing",
            latency_ms=5,
            status_code=404,
        )
        snapshot = metrics.snapshot()
        self.assertEqual(
            snapshot["requests_total"],
            2,
        )
        self.assertEqual(
            snapshot["errors_total"],
            1,
        )

    def test_heartbeat(self):
        registry = HeartbeatRegistry()
        registry.beat("WATCHDOG")
        items = registry.snapshot()
        self.assertEqual(
            items[0].status,
            "RUNNING",
        )

    def test_mock_notification(self):
        queue = NotificationQueue()
        item = queue.enqueue(
            channel="EMAIL",
            severity="INFO",
            subject="Test",
            body="Test",
        )
        result = MockNotificationAdapter(
            "EMAIL"
        ).deliver(item)
        self.assertFalse(
            result[
                "external_delivery_performed"
            ]
        )

    def test_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "source.db"
            connection = sqlite3.connect(
                str(database)
            )
            connection.execute(
                "CREATE TABLE test(id INTEGER)"
            )
            connection.commit()
            connection.close()

            manager = BackupManager(
                source_database=database,
                backup_root=root / "backups",
            )
            backup = manager.create_backup()
            validation = manager.validate_backup(
                Path(backup["backup_path"])
            )
            self.assertTrue(validation["valid"])

    def test_service_restart_block(self):
        result = SafeServiceManager().request(
            service_name="WATCHDOG",
            action="RESTART",
        )
        self.assertEqual(
            result["status"],
            "BLOCKED",
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                SaaSOperationsCertificationService()
                .evaluate(output_dir=Path(directory))
            )
            self.assertEqual(result["status"], "PASS")

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                SaaSOperationsCertificationService()
                .evaluate(output_dir=Path(directory))
            )
            self.assertFalse(
                result["actual_broker_write_performed"]
            )
            self.assertEqual(
                result["actual_paper_orders_submitted"],
                0,
            )
            self.assertEqual(
                result["actual_live_orders_submitted"],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
