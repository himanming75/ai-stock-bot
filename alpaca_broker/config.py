from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse

from .errors import AlpacaConfigurationError


PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"


@dataclass(frozen=True)
class AlpacaPaperConfig:
    base_url: str = PAPER_BASE_URL
    timeout_seconds: float = 10.0
    max_retries: int = 2
    network_read_enabled: bool = False
    network_write_enabled: bool = False
    user_agent: str = "ai-stock-bot-paper/1.0"

    def validate(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https":
            raise AlpacaConfigurationError("Alpaca base URL must use HTTPS")
        if self.base_url.rstrip("/") != PAPER_BASE_URL:
            if self.base_url.rstrip("/") == LIVE_BASE_URL:
                raise AlpacaConfigurationError("live Alpaca URL is forbidden")
            raise AlpacaConfigurationError("only the Alpaca paper URL is allowed")
        if self.timeout_seconds <= 0:
            raise AlpacaConfigurationError("timeout_seconds must be positive")
        if self.max_retries < 0 or self.max_retries > 5:
            raise AlpacaConfigurationError("max_retries must be between 0 and 5")
        if self.network_write_enabled and not self.network_read_enabled:
            raise AlpacaConfigurationError("write opt-in requires read opt-in")


@dataclass(frozen=True)
class CredentialLoader:
    key_env: str = "APCA_API_KEY_ID"
    secret_env: str = "APCA_API_SECRET_KEY"

    def load(self, environ: dict[str, str] | None = None) -> tuple[str, str]:
        source = os.environ if environ is None else environ
        key = source.get(self.key_env, "").strip()
        secret = source.get(self.secret_env, "").strip()
        if not key or not secret:
            raise AlpacaConfigurationError(
                f"missing credentials: {self.key_env} and {self.secret_env}"
            )
        return key, secret

    @staticmethod
    def redact(value: str) -> str:
        if len(value) <= 4:
            return "****"
        return value[:2] + ("*" * (len(value) - 4)) + value[-2:]
