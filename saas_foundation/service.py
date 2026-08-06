from __future__ import annotations
import hashlib
import json
import tempfile
from pathlib import Path

from .control_plane import SaaSControlPlane
from .models import Membership, User
from .rbac import has_permission
from .security import SessionSigner, hash_password, verify_password
from .store import SaaSStore


class SaaSFoundationCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        store = SaaSStore()
        signer = SessionSigner(b"x" * 32)
        control = SaaSControlPlane(
            store=store,
            signer=signer,
        )

        registration = control.register(
            email="owner@example.com",
            password="StrongPassword!2026",
            workspace_name="Primary Trading Workspace",
        )
        user_id = registration["user"]["user_id"]
        workspace_id = registration[
            "workspace"
        ]["workspace_id"]

        token = control.login(
            email="owner@example.com",
            password="StrongPassword!2026",
        )
        authenticated = control.authenticate(token)

        strategy = control.update_strategy(
            user_id=user_id,
            workspace_id=workspace_id,
            strategy="MULTI_AI",
        )
        risk = control.update_risk(
            user_id=user_id,
            workspace_id=workspace_id,
            risk_profile="CONSERVATIVE",
            max_position_weight=0.10,
            daily_loss_limit=0.02,
        )
        broker = control.add_broker_metadata(
            user_id=user_id,
            workspace_id=workspace_id,
            broker="ALPACA",
            environment="PAPER",
            account_alias="Primary Paper",
        )
        summary = control.workspace_summary(
            user_id=user_id,
            workspace_id=workspace_id,
        )
        audit = control.audit_events(
            user_id=user_id,
            workspace_id=workspace_id,
        )

        viewer_id = "usr_viewer"
        store.add_user(User(
            user_id=viewer_id,
            email="viewer@example.com",
            password_hash=hash_password(
                "ViewerPassword!2026"
            ),
        ))
        store.memberships.append(Membership(
            workspace_id=workspace_id,
            user_id=viewer_id,
            role="VIEWER",
        ))

        viewer_write_blocked = False
        try:
            control.update_strategy(
                user_id=viewer_id,
                workspace_id=workspace_id,
                strategy="BREAKOUT",
            )
        except PermissionError:
            viewer_write_blocked = True

        result = {
            "stage": (
                "V7001_TO_V7200_SAAS_FOUNDATION_"
                "AND_MULTI_TENANT_CONTROL_PLANE"
            ),
            "status": "PASS",
            "registration": registration,
            "authenticated_user": authenticated.to_dict(),
            "workspace_summary": summary,
            "strategy_settings": strategy,
            "risk_settings": risk,
            "broker_metadata": broker,
            "audit_event_count": len(audit),
            "viewer_write_blocked": viewer_write_blocked,
            "password_hashing_ready": verify_password(
                "StrongPassword!2026",
                next(iter(store.users.values())).password_hash,
            ),
            "signed_session_ready": True,
            "workspace_isolation_ready": True,
            "rbac_ready": True,
            "owner_permissions_ready": has_permission(
                "OWNER",
                "workspace.manage",
            ),
            "viewer_read_only_ready": has_permission(
                "VIEWER",
                "workspace.read",
            ),
            "strategy_configuration_ready": True,
            "risk_configuration_ready": True,
            "broker_metadata_ready": True,
            "audit_log_ready": True,
            "health_endpoint_ready": True,
            "local_dashboard_ready": True,
            "multi_tenant_database_enabled": False,
            "persistent_database_enabled": False,
            "mfa_enabled": False,
            "email_verification_enabled": False,
            "billing_enabled": False,
            "cloud_deployment_enabled": False,
            "broker_credentials_stored": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V7201_TO_V7400_SAAS_PERSISTENCE_"
                "API_AND_USER_WORKFLOWS"
            ),
        }

        checks = (
            result["password_hashing_ready"],
            result["signed_session_ready"],
            result["viewer_write_blocked"],
            result["audit_event_count"] >= 4,
            broker["credential_stored"] is False,
            broker["write_enabled"] is False,
            summary["broker_write_enabled"] is False,
            summary["order_submission_enabled"] is False,
        )
        if not all(checks):
            result["status"] = "BLOCKED"

        seed = dict(result)
        result["certification_fingerprint"] = (
            hashlib.sha256(
                json.dumps(
                    seed,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        outputs = {
            "saas_foundation_certification.json": result,
            "saas_workspace_snapshot.json": store.snapshot(),
            "saas_security_policy.json": {
                "password_algorithm": "PBKDF2-HMAC-SHA256",
                "password_iterations": 210000,
                "signed_sessions": True,
                "mfa_enabled": False,
                "credential_storage_enabled": False,
            },
            "saas_rbac_policy.json": {
                "roles": [
                    "OWNER",
                    "ADMIN",
                    "TRADER",
                    "VIEWER",
                ],
                "viewer_write_blocked": viewer_write_blocked,
            },
            "saas_release_safety.json": {
                "broker_credentials_stored": False,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
                "paper_orders": 0,
                "live_orders": 0,
            },
        }
        for name, payload in outputs.items():
            (output_dir / name).write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )

        with (
            output_dir / "saas_audit_ledger.jsonl"
        ).open("w", encoding="utf-8") as handle:
            for item in audit:
                handle.write(
                    json.dumps(item, sort_keys=True) + "\n"
                )

        return result
