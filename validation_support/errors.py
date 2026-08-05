from __future__ import annotations
from typing import Any


class ApiErrorClassifier:
    def classify(
        self,
        *,
        status_code: int | None,
        message: str,
        headers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = (message or "").lower()
        headers = headers or {}

        category = "UNKNOWN"
        retryable = False
        operator_action = "REVIEW_RESPONSE"

        if status_code in {401, 403}:
            category = "AUTHENTICATION"
            operator_action = "RELOAD_OR_ROTATE_PAPER_CREDENTIALS"
        elif status_code == 429:
            category = "RATE_LIMIT"
            retryable = True
            operator_action = "WAIT_FOR_RATE_LIMIT_RESET"
        elif status_code is not None and status_code >= 500:
            category = "BROKER_SERVER"
            retryable = True
            operator_action = "WAIT_AND_RETRY_READ_ONLY_REQUEST"
        elif status_code in {400, 404, 422}:
            category = "REQUEST_OR_SCHEMA"
            operator_action = "CHECK_ENDPOINT_AND_RESPONSE_SCHEMA"
        elif "timeout" in text or "timed out" in text:
            category = "TIMEOUT"
            retryable = True
            operator_action = "CHECK_NETWORK_THEN_RETRY_READ_ONLY_REQUEST"
        elif "dns" in text or "name resolution" in text:
            category = "NETWORK_DNS"
            retryable = True
            operator_action = "CHECK_DNS_AND_NETWORK"
        elif "ssl" in text or "certificate" in text:
            category = "TLS"
            operator_action = "CHECK_SYSTEM_TIME_AND_CERTIFICATES"

        return {
            "category": category,
            "retryable": retryable,
            "operator_action": operator_action,
            "status_code": status_code,
            "rate_limit_remaining": headers.get(
                "x-ratelimit-remaining"
            ),
            "rate_limit_reset": headers.get("x-ratelimit-reset"),
            "automatic_retry_performed": False,
        }
