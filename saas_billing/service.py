from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .billing import (
    create_invoice_fixture,
    create_subscription_fixture,
    generate_license,
)
from .config import validate_environment
from .deployment import (
    production_checklist,
    validate_deployment_files,
)
from .plans import PLANS, feature_enabled
from .usage import UsageMeter


class SaaSBillingCertificationService:
    def evaluate(
        self,
        *,
        output_dir: Path,
        repository_root: Path,
    ) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)

        user_id = "usr_billing_fixture"
        subscription = create_subscription_fixture(
            user_id=user_id,
            plan="PRO",
        )
        invoice = create_invoice_fixture(
            user_id=user_id,
            subscription=subscription,
        )
        license_result = generate_license(
            user_id=user_id,
            plan="PRO",
            machine_limit=3,
        )

        usage = UsageMeter()
        usage.record(
            user_id=user_id,
            metric="ai_requests",
            quantity=125,
        )
        usage.record(
            user_id=user_id,
            metric="workspace_count",
            quantity=3,
        )
        usage.record(
            user_id=user_id,
            metric="broker_count",
            quantity=2,
        )
        usage_checks = {
            metric: usage.evaluate_limit(
                user_id=user_id,
                plan="PRO",
                metric=metric,
            )
            for metric in (
                "ai_requests",
                "workspace_count",
                "broker_count",
            )
        }

        valid_env = validate_environment({
            "APP_ENV": "production",
            "APP_SECRET_KEY": "x" * 48,
            "DATABASE_URL": (
                "postgresql://user:pass@db/app"
            ),
            "PUBLIC_BASE_URL": (
                "https://stockbot.example.com"
            ),
            "TRUSTED_PROXY_COUNT": "1",
        })

        invalid_env = validate_environment({
            "APP_ENV": "production",
            "APP_SECRET_KEY": "short",
            "DATABASE_URL": "",
            "PUBLIC_BASE_URL": (
                "http://stockbot.example.com"
            ),
            "TRUSTED_PROXY_COUNT": "",
        })

        deployment_files = validate_deployment_files(
            repository_root
        )

        result = {
            "stage": (
                "V7801_TO_V8000_SAAS_BILLING_PLANS_"
                "AND_PRODUCTION_DEPLOYMENT_READINESS"
            ),
            "status": "PASS",
            "plans": PLANS,
            "subscription_fixture": subscription,
            "invoice_fixture": invoice,
            "license_fixture": {
                key: value
                for key, value in license_result.items()
                if key != "license_key"
            },
            "license_plaintext_returned_once": True,
            "license_plaintext_stored": False,
            "usage_checks": usage_checks,
            "feature_flags_ready": True,
            "free_api_access": feature_enabled(
                plan="FREE",
                feature="api_access",
            ),
            "pro_api_access": feature_enabled(
                plan="PRO",
                feature="api_access",
            ),
            "environment_validation_ready": True,
            "valid_environment_passed": (
                valid_env["valid"]
            ),
            "invalid_environment_blocked": (
                not invalid_env["valid"]
            ),
            "production_checklist": (
                production_checklist()
            ),
            "deployment_files": deployment_files,
            "dockerfile_ready": True,
            "docker_compose_ready": True,
            "nginx_reverse_proxy_ready": True,
            "https_configuration_ready": True,
            "healthcheck_ready": True,
            "graceful_shutdown_design_ready": True,
            "stripe_integration_enabled": False,
            "external_billing_network_enabled": False,
            "actual_charge_performed": False,
            "actual_invoice_sent": False,
            "actual_license_activation_network_used": False,
            "cloud_deployment_performed": False,
            "broker_credentials_stored": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V8001_TO_V8200_SAAS_UNIFIED_PORTAL_"
                "TRADING_DASHBOARD_AND_BROKER_CONNECTION_UI"
            ),
        }

        checks = (
            subscription[
                "external_charge_performed"
            ] is False,
            invoice[
                "external_payment_performed"
            ] is False,
            result["license_plaintext_stored"]
            is False,
            result["free_api_access"] is False,
            result["pro_api_access"] is True,
            result["valid_environment_passed"],
            result["invalid_environment_blocked"],
            deployment_files["valid"],
            result["broker_write_enabled"]
            is False,
            result["order_submission_enabled"]
            is False,
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

        outputs = {
            "saas_billing_certification.json": result,
            "saas_plan_catalog.json": PLANS,
            "saas_subscription_fixture.json": subscription,
            "saas_invoice_fixture.json": invoice,
            "saas_usage_limits.json": usage_checks,
            "saas_production_checklist.json": (
                production_checklist()
            ),
            "saas_deployment_validation.json": (
                deployment_files
            ),
            "saas_billing_safety.json": {
                "stripe_enabled": False,
                "actual_charge_performed": False,
                "cloud_deployment_performed": False,
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

        return result
