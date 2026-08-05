from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from .config import ReadConfig
from .errors import (
    AlpacaAuthenticationError,
    AlpacaNetworkError,
    AlpacaRateLimitError,
)


class ReadOnlyHttpClient:
    ALLOWED_METHODS = {"GET"}

    def __init__(
        self,
        config: ReadConfig,
        sleep: Callable[[float], None] = time.sleep,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self.config = config
        self.sleep = sleep
        self.opener = opener

    def get_json(self, path: str) -> Any:
        return self.request_json("GET", path)

    def request_json(self, method: str, path: str) -> Any:
        method = method.upper()
        if method not in self.ALLOWED_METHODS:
            raise ValueError("READ_ONLY_HTTP_METHOD_REQUIRED")
        if not self.config.actual_network_enabled:
            raise AlpacaNetworkError("ACTUAL_NETWORK_READ_NOT_ENABLED")
        if not self.config.credentials_present:
            raise AlpacaAuthenticationError("ALPACA_PAPER_CREDENTIALS_MISSING")
        if not self.config.paper_endpoint_enforced:
            raise AlpacaNetworkError("PAPER_ENDPOINT_NOT_ENFORCED")

        url = f"{self.config.base_url}{path}"
        headers = {
            "APCA-API-KEY-ID": self.config.api_key,
            "APCA-API-SECRET-KEY": self.config.secret_key,
            "Accept": "application/json",
            "User-Agent": "ai-stock-bot-v470-read-only",
        }

        last_error: Exception | None = None
        for attempt in range(1, self.config.maximum_attempts + 1):
            request = urllib.request.Request(
                url=url,
                headers=headers,
                method="GET",
            )
            try:
                with self.opener(
                    request,
                    timeout=self.config.timeout_seconds,
                ) as response:
                    body = response.read().decode("utf-8")
                    return json.loads(body)
            except urllib.error.HTTPError as exc:
                if exc.code in {401, 403}:
                    raise AlpacaAuthenticationError(
                        f"ALPACA_AUTHENTICATION_FAILED:{exc.code}"
                    ) from exc
                if exc.code == 429:
                    last_error = AlpacaRateLimitError("ALPACA_RATE_LIMITED")
                elif 500 <= exc.code <= 599:
                    last_error = AlpacaNetworkError(
                        f"ALPACA_SERVER_ERROR:{exc.code}"
                    )
                else:
                    raise AlpacaNetworkError(
                        f"ALPACA_HTTP_ERROR:{exc.code}"
                    ) from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = AlpacaNetworkError(
                    f"ALPACA_NETWORK_ERROR:{type(exc).__name__}"
                )

            if attempt < self.config.maximum_attempts:
                self.sleep(self.config.backoff_seconds * attempt)

        if last_error is None:
            raise AlpacaNetworkError("ALPACA_READ_FAILED")
        raise last_error
