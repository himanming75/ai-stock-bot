from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from saas_billing.billing import (
    create_invoice_fixture,
    create_subscription_fixture,
    generate_license,
)
from saas_billing.config import validate_environment
from saas_billing.plans import feature_enabled
from saas_billing.service import (
    SaaSBillingCertificationService,
)
from saas_billing.usage import UsageMeter


class Tests(unittest.TestCase):
    def test_plans(self):
        self.assertFalse(
            feature_enabled(
                plan="FREE",
                feature="api_access",
            )
        )
        self.assertTrue(
            feature_enabled(
                plan="PRO",
                feature="api_access",
            )
        )

    def test_usage_limits(self):
        meter = UsageMeter()
        meter.record(
            user_id="u1",
            metric="ai_requests",
            quantity=21,
        )
        result = meter.evaluate_limit(
            user_id="u1",
            plan="FREE",
            metric="ai_requests",
        )
        self.assertFalse(result["allowed"])

    def test_invoice_is_fixture_only(self):
        subscription = create_subscription_fixture(
            user_id="u1",
            plan="PRO",
        )
        invoice = create_invoice_fixture(
            user_id="u1",
            subscription=subscription,
        )
        self.assertFalse(
            invoice[
                "external_payment_performed"
            ]
        )

    def test_license_plaintext_not_storage_value(self):
        license_result = generate_license(
            user_id="u1",
            plan="PRO",
            machine_limit=2,
        )
        self.assertNotEqual(
            license_result["license_key"],
            license_result[
                "license_key_hash"
            ],
        )

    def test_environment_validation(self):
        valid = validate_environment({
            "APP_ENV": "production",
            "APP_SECRET_KEY": "x" * 48,
            "DATABASE_URL": "postgresql://db/app",
            "PUBLIC_BASE_URL": (
                "https://stockbot.example.com"
            ),
            "TRUSTED_PROXY_COUNT": "1",
        })
        self.assertTrue(valid["valid"])

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (
                "Dockerfile",
                "docker-compose.yml",
                "deploy/nginx.conf",
                "deploy/.env.production.example",
                "deploy/PRODUCTION_CHECKLIST.md",
            ):
                path = root / relative
                path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                path.write_text("fixture", encoding="utf-8")

            result = (
                SaaSBillingCertificationService()
                .evaluate(
                    output_dir=root / "output",
                    repository_root=root,
                )
            )
            self.assertEqual(result["status"], "PASS")

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (
                "Dockerfile",
                "docker-compose.yml",
                "deploy/nginx.conf",
                "deploy/.env.production.example",
                "deploy/PRODUCTION_CHECKLIST.md",
            ):
                path = root / relative
                path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                path.write_text("fixture", encoding="utf-8")

            result = (
                SaaSBillingCertificationService()
                .evaluate(
                    output_dir=root / "output",
                    repository_root=root,
                )
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
