from __future__ import annotations
import unittest

from secure_control_plane.policies import ControlPolicyEngine
from secure_control_plane.requests import (
    ApprovalReviewer,
    ChangeRequestFactory,
    IdempotencyRegistry,
)
from secure_control_plane.security import (
    OperatorIdentity,
    SensitiveValueRedactor,
)


class Tests(unittest.TestCase):
    def test_viewer_cannot_create_request(self):
        with self.assertRaises(PermissionError):
            ChangeRequestFactory().create(
                identity=OperatorIdentity("v", "VIEWER"),
                request_type="CONFIGURATION_CHANGE",
                subject="x",
                proposed_value={},
                reason="x",
                idempotency_key="x",
            )

    def test_self_approval_rejected(self):
        operator = OperatorIdentity("o", "ADMIN")
        request = ChangeRequestFactory().create(
            identity=operator,
            request_type="CONFIGURATION_CHANGE",
            subject="x",
            proposed_value={},
            reason="x",
            idempotency_key="x",
        )
        with self.assertRaises(PermissionError):
            ApprovalReviewer().review(
                identity=operator,
                request=request,
                decision="APPROVE_PREVIEW",
                comment="x",
            )

    def test_live_mode_rejected(self):
        operator = OperatorIdentity("o", "OPERATOR")
        request = ChangeRequestFactory().create(
            identity=operator,
            request_type="CONFIGURATION_CHANGE",
            subject="x",
            proposed_value={"broker_mode": "live"},
            reason="x",
            idempotency_key="x",
        )
        self.assertFalse(
            ControlPolicyEngine().evaluate(request)["policy_pass"]
        )

    def test_sensitive_value_redacted(self):
        value = SensitiveValueRedactor().redact({
            "api_key": "secret",
            "safe": "visible",
        })
        self.assertEqual(value["api_key"], "[REDACTED]")
        self.assertEqual(value["safe"], "visible")

    def test_duplicate_idempotency_key(self):
        registry = IdempotencyRegistry()
        self.assertTrue(registry.register("x"))
        self.assertFalse(registry.register("x"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
