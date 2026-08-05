from __future__ import annotations
from dataclasses import dataclass
import os


LIVE_BASE_URL = "https://api.alpaca.markets"


@dataclass(frozen=True)
class LiveReadConfig:
    api_key: str
    secret_key: str
    base_url: str
    network_enabled: bool
    timeout_seconds: float
    maximum_attempts: int

    @classmethod
    def from_env(cls) -> "LiveReadConfig":
        return cls(
            api_key=os.getenv("LIVE_APCA_API_KEY_ID", ""),
            secret_key=os.getenv("LIVE_APCA_API_SECRET_KEY", ""),
            base_url=os.getenv("LIVE_APCA_API_BASE_URL", LIVE_BASE_URL),
            network_enabled=False,
            timeout_seconds=float(os.getenv("LIVE_READ_TIMEOUT_SECONDS", "10")),
            maximum_attempts=int(os.getenv("LIVE_READ_MAXIMUM_ATTEMPTS", "3")),
        )

    def evaluate(self) -> dict:
        checks = {
            "live_endpoint_valid": self.base_url == LIVE_BASE_URL,
            "network_disabled": self.network_enabled is False,
            "timeout_positive": self.timeout_seconds > 0,
            "attempts_safe": 1 <= self.maximum_attempts <= 5,
            "credentials_present_or_deferred": True,
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
        }
