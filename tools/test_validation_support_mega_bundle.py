from __future__ import annotations
import unittest

from validation_support.errors import ApiErrorClassifier
from validation_support.retry import RateLimitDetector, RetryPolicy
from validation_support.schema import ResponseSchemaValidator


class Tests(unittest.TestCase):
    def test_auth_error_not_retryable(self):
        result = ApiErrorClassifier().classify(
            status_code=401,
            message="unauthorized",
        )
        self.assertEqual(result["category"], "AUTHENTICATION")
        self.assertFalse(result["retryable"])

    def test_rate_limit_classified(self):
        result = ApiErrorClassifier().classify(
            status_code=429,
            message="too many requests",
        )
        self.assertEqual(result["category"], "RATE_LIMIT")
        self.assertTrue(result["retryable"])

    def test_retry_preview_not_automatic(self):
        result = RetryPolicy().plan(
            category="TIMEOUT",
            attempt=1,
        )
        self.assertTrue(result["retry_allowed"])
        self.assertFalse(result["automatic_retry_enabled"])

    def test_rate_limit_detector(self):
        result = RateLimitDetector().detect(
            status_code=200,
            headers={"x-ratelimit-remaining": "0"},
        )
        self.assertTrue(result["rate_limited"])

    def test_account_schema(self):
        result = ResponseSchemaValidator().validate(
            schema_name="account",
            value={
                "id": "x",
                "status": "ACTIVE",
                "cash": "1",
                "equity": "1",
                "buying_power": "2",
            },
        )
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
