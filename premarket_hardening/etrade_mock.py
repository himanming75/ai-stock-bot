from __future__ import annotations
from dataclasses import dataclass


@dataclass
class MockToken:
    request_token: str
    access_token: str
    expires_in_seconds: int


class ETradeMockClient:
    def __init__(self) -> None:
        self.attempts = 0
        self.write_calls = 0

    def request_token(self) -> MockToken:
        return MockToken(
            request_token="mock-request-token",
            access_token="",
            expires_in_seconds=300,
        )

    def exchange_token(self, verifier: str) -> MockToken:
        if verifier != "123456":
            raise ValueError("INVALID_VERIFIER")
        return MockToken(
            request_token="mock-request-token",
            access_token="mock-access-token",
            expires_in_seconds=7200,
        )

    def read_accounts(
        self,
        *,
        fail_before_success: int = 2,
        max_attempts: int = 3,
    ) -> dict:
        while self.attempts < max_attempts:
            self.attempts += 1
            if self.attempts <= fail_before_success:
                continue
            return {
                "status": "PASS",
                "attempts": self.attempts,
                "accounts": [
                    {
                        "account_id": "MOCK_ETRADE_PRIMARY",
                        "type": "BROKERAGE",
                        "read_only": True,
                    }
                ],
            }
        return {
            "status": "BLOCKED",
            "attempts": self.attempts,
            "reason": "RETRY_EXHAUSTED",
        }

    def submit_order(self) -> None:
        self.write_calls += 1
        raise PermissionError("ETRADE_WRITE_DISABLED")
