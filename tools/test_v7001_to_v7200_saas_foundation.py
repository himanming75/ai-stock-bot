from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from saas_foundation.control_plane import SaaSControlPlane
from saas_foundation.models import Membership, User
from saas_foundation.security import (
    SessionSigner,
    hash_password,
    verify_password,
)
from saas_foundation.service import (
    SaaSFoundationCertificationService,
)
from saas_foundation.store import SaaSStore


class Tests(unittest.TestCase):
    def test_password_hashing(self):
        encoded = hash_password(
            "StrongPassword!2026"
        )
        self.assertTrue(
            verify_password(
                "StrongPassword!2026",
                encoded,
            )
        )
        self.assertFalse(
            verify_password(
                "WrongPassword!2026",
                encoded,
            )
        )

    def test_session_signing(self):
        signer = SessionSigner(b"z" * 32)
        token = signer.issue(user_id="usr_1")
        self.assertEqual(
            signer.verify(token)["user_id"],
            "usr_1",
        )

    def test_registration_and_login(self):
        control = SaaSControlPlane(
            store=SaaSStore(),
            signer=SessionSigner(b"y" * 32),
        )
        control.register(
            email="owner@example.com",
            password="StrongPassword!2026",
            workspace_name="Workspace",
        )
        token = control.login(
            email="owner@example.com",
            password="StrongPassword!2026",
        )
        self.assertTrue(token)

    def test_viewer_cannot_write(self):
        store = SaaSStore()
        control = SaaSControlPlane(
            store=store,
            signer=SessionSigner(b"x" * 32),
        )
        registration = control.register(
            email="owner@example.com",
            password="StrongPassword!2026",
            workspace_name="Workspace",
        )
        workspace_id = registration[
            "workspace"
        ]["workspace_id"]
        viewer = User(
            user_id="usr_viewer",
            email="viewer@example.com",
            password_hash=hash_password(
                "ViewerPassword!2026"
            ),
        )
        store.add_user(viewer)
        store.memberships.append(Membership(
            workspace_id=workspace_id,
            user_id=viewer.user_id,
            role="VIEWER",
        ))
        with self.assertRaises(PermissionError):
            control.update_strategy(
                user_id=viewer.user_id,
                workspace_id=workspace_id,
                strategy="BREAKOUT",
            )

    def test_broker_metadata_is_safe(self):
        store = SaaSStore()
        control = SaaSControlPlane(
            store=store,
            signer=SessionSigner(b"w" * 32),
        )
        registration = control.register(
            email="owner@example.com",
            password="StrongPassword!2026",
            workspace_name="Workspace",
        )
        connection = control.add_broker_metadata(
            user_id=registration["user"]["user_id"],
            workspace_id=registration[
                "workspace"
            ]["workspace_id"],
            broker="ALPACA",
            environment="PAPER",
            account_alias="Paper",
        )
        self.assertFalse(connection["credential_stored"])
        self.assertFalse(connection["write_enabled"])

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                SaaSFoundationCertificationService()
                .evaluate(output_dir=Path(directory))
            )
            self.assertEqual(result["status"], "PASS")

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                SaaSFoundationCertificationService()
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
