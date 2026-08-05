from __future__ import annotations
from dataclasses import dataclass
import os


PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"


@dataclass(frozen=True)
class ReadConfig:
    api_key: str
    secret_key: str
    base_url: str
    timeout_seconds: float
    maximum_attempts: int
    backoff_seconds: float
    actual_network_enabled: bool

    @property
    def credentials_present(self) -> bool:
        return bool(self.api_key.strip() and self.secret_key.strip())

    @property
    def paper_endpoint_enforced(self) -> bool:
        return self.base_url.rstrip("/") == PAPER_BASE_URL


def _true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> ReadConfig:
    base_url = os.getenv("APCA_API_BASE_URL", PAPER_BASE_URL).strip().rstrip("/")
    if base_url == LIVE_BASE_URL:
        raise ValueError("LIVE_ALPACA_ENDPOINT_REJECTED")
    if base_url != PAPER_BASE_URL:
        raise ValueError("NON_PAPER_ALPACA_ENDPOINT_REJECTED")

    timeout = float(os.getenv("ALPACA_PAPER_READ_TIMEOUT_SECONDS", "10"))
    attempts = int(os.getenv("ALPACA_PAPER_READ_MAX_ATTEMPTS", "3"))
    backoff = float(os.getenv("ALPACA_PAPER_READ_BACKOFF_SECONDS", "0.5"))

    if timeout <= 0:
        raise ValueError("TIMEOUT_MUST_BE_POSITIVE")
    if attempts < 1 or attempts > 5:
        raise ValueError("MAX_ATTEMPTS_OUT_OF_RANGE")
    if backoff < 0 or backoff > 10:
        raise ValueError("BACKOFF_OUT_OF_RANGE")

    return ReadConfig(
        api_key=os.getenv("APCA_API_KEY_ID", ""),
        secret_key=os.getenv("APCA_API_SECRET_KEY", ""),
        base_url=base_url,
        timeout_seconds=timeout,
        maximum_attempts=attempts,
        backoff_seconds=backoff,
        actual_network_enabled=_true("ALPACA_PAPER_READ_ENABLE"),
    )
