from __future__ import annotations
import tempfile
import time
import unittest
from pathlib import Path

from saas_security.control_plane import (
    SaaSSecurityControlPlane,
)
from saas_security.crypto import totp_code
from saas_security.database import SecurityDatabase
from saas_security.repository import SecurityRepository
from saas_security.service import (
    SaaSSecurityCertificationService,
)


class Tests(unittest.TestCase):
    def control(self, path: Path):
        database = SecurityDatabase(path)
        control = SaaSSecurityControlPlane(
            SecurityRepository(database)
        )
        return database, control

    def test_account_lockout(self):
        with tempfile.TemporaryDirectory() as directory:
            database, control = self.control(
                Path(directory) / "security.db"
            )
            result = control.register(
                email="user@example.com",
                password="StrongPassword!2026",
                workspace_name="Workspace",
            )
            for _ in range(5):
                with self.assertRaises(
                    PermissionError
                ):
                    control.login(
                        email="user@example.com",
                        password="WrongPassword!2026",
                    )
            user = control.repository.get_user(
                result["user"]["user_id"]
            )
            self.assertTrue(user["is_locked"])
            database.close()

    def test_password_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            database, control = self.control(
                Path(directory) / "security.db"
            )
            control.register(
                email="user@example.com",
                password="StrongPassword!2026",
                workspace_name="Workspace",
            )
            request = control.create_password_reset_token(
                email="user@example.com"
            )
            control.reset_password(
                token=request["token"],
                new_password="NewStrongPassword!2026",
            )
            login = control.login(
                email="user@example.com",
                password="NewStrongPassword!2026",
            )
            self.assertTrue(login["access_token"])
            database.close()

    def test_mfa(self):
        with tempfile.TemporaryDirectory() as directory:
            database, control = self.control(
                Path(directory) / "security.db"
            )
            result = control.register(
                email="user@example.com",
                password="StrongPassword!2026",
                workspace_name="Workspace",
            )
            user_id = result["user"]["user_id"]
            setup = control.begin_mfa(
                user_id=user_id
            )
            control.confirm_mfa(
                user_id=user_id,
                code=totp_code(
                    setup["secret"],
                    at_time=int(time.time()),
                ),
            )
            login = control.login(
                email="user@example.com",
                password="StrongPassword!2026",
                mfa_code=totp_code(
                    setup["secret"]
                ),
            )
            self.assertTrue(login["access_token"])
            database.close()

    def test_api_token_plaintext_not_stored(self):
        with tempfile.TemporaryDirectory() as directory:
            database, control = self.control(
                Path(directory) / "security.db"
            )
            result = control.register(
                email="user@example.com",
                password="StrongPassword!2026",
                workspace_name="Workspace",
            )
            token = control.create_api_token(
                actor_user_id=result["user"]["user_id"],
                workspace_id=result["workspace"][
                    "workspace_id"
                ],
                name="Read Only",
                scopes=["workspace.read"],
            )
            row = database.query_one(
                """
                SELECT token_hash
                FROM api_tokens
                WHERE token_id = ?
                """,
                (
                    token["metadata"]["token_id"],
                ),
            )
            self.assertNotEqual(
                row["token_hash"],
                token["token"],
            )
            database.close()

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                SaaSSecurityCertificationService()
                .evaluate(output_dir=Path(directory))
            )
            self.assertEqual(result["status"], "PASS")

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                SaaSSecurityCertificationService()
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
