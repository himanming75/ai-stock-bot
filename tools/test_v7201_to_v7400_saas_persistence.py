from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from saas_persistence.control_plane import (
    PersistentSaaSControlPlane,
)
from saas_persistence.database import SQLiteDatabase
from saas_persistence.repository import SaaSRepository
from saas_persistence.security import SessionSigner
from saas_persistence.service import (
    SaaSPersistenceCertificationService,
)


class Tests(unittest.TestCase):
    def control(self, path: Path):
        database = SQLiteDatabase(path)
        return (
            database,
            PersistentSaaSControlPlane(
                repository=SaaSRepository(database),
                signer=SessionSigner(b"s" * 32),
            ),
        )

    def test_persistent_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "saas.db"
            database, control = self.control(path)
            result = control.register(
                email="owner@example.com",
                password="StrongPassword!2026",
                workspace_name="Workspace",
            )
            user_id = result["user"]["user_id"]
            database.close()

            database2, control2 = self.control(path)
            self.assertTrue(
                control2.repository.get_user(user_id)
            )
            database2.close()

    def test_persistent_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "saas.db"
            database, control = self.control(path)
            result = control.register(
                email="owner@example.com",
                password="StrongPassword!2026",
                workspace_name="Workspace",
            )
            user_id = result["user"]["user_id"]
            workspace_id = result["workspace"][
                "workspace_id"
            ]
            control.update_strategy(
                user_id=user_id,
                workspace_id=workspace_id,
                strategy="MULTI_AI",
            )
            database.close()

            database2, control2 = self.control(path)
            summary = control2.workspace_summary(
                user_id=user_id,
                workspace_id=workspace_id,
            )
            self.assertEqual(
                summary["settings"]["selected_strategy"],
                "MULTI_AI",
            )
            database2.close()

    def test_safe_broker_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            database, control = self.control(
                Path(directory) / "saas.db"
            )
            result = control.register(
                email="owner@example.com",
                password="StrongPassword!2026",
                workspace_name="Workspace",
            )
            connection = control.add_broker_metadata(
                user_id=result["user"]["user_id"],
                workspace_id=result["workspace"][
                    "workspace_id"
                ],
                broker="ALPACA",
                environment="PAPER",
                account_alias="Paper",
            )
            self.assertEqual(
                connection["credential_stored"],
                0,
            )
            self.assertEqual(
                connection["write_enabled"],
                0,
            )
            database.close()

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                SaaSPersistenceCertificationService()
                .evaluate(output_dir=Path(directory))
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(
                result["restart_restore_ready"]
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                SaaSPersistenceCertificationService()
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
