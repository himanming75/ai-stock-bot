from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from .execution_config import ExecutionConfig


DATA_BASE_URL = "https://data.alpaca.markets"


class AlpacaMarketDataReadHttp:
    def __init__(
        self,
        config: ExecutionConfig,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.opener = opener
        self.sleep = sleep

    def latest_trade_price(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if not normalized or not normalized.replace(".", "").isalnum():
            raise ValueError("INVALID_SYMBOL")
        if not self.config.credentials_present:
            raise PermissionError("PAPER_CREDENTIALS_MISSING")
        if not self.config.network_enabled:
            raise PermissionError("PAPER_EXECUTION_NETWORK_DISABLED")

        request = urllib.request.Request(
            url=f"{DATA_BASE_URL}/v2/stocks/{normalized}/trades/latest",
            headers={
                "APCA-API-KEY-ID": self.config.api_key,
                "APCA-API-SECRET-KEY": self.config.secret_key,
                "Accept": "application/json",
                "User-Agent": "ai-stock-bot-p2a-market-data",
            },
            method="GET",
        )

        last_error: Exception | None = None
        for attempt in range(1, self.config.maximum_attempts + 1):
            try:
                with self.opener(
                    request,
                    timeout=self.config.timeout_seconds,
                ) as response:
                    value = json.loads(response.read().decode("utf-8"))
                    trade = value.get("trade", {})
                    price = trade.get("p")
                    if price is None:
                        raise RuntimeError("LATEST_TRADE_PRICE_MISSING")
                    return str(price)
            except urllib.error.HTTPError as exc:
                body = ""
                try:
                    body = exc.read().decode("utf-8")
                except Exception:
                    pass
                if exc.code in {401, 403, 404}:
                    raise RuntimeError(
                        f"ALPACA_DATA_HTTP_{exc.code}:{body}"
                    ) from exc
                if exc.code == 429 or 500 <= exc.code <= 599:
                    last_error = RuntimeError(
                        f"ALPACA_DATA_RETRYABLE_HTTP_{exc.code}:{body}"
                    )
                else:
                    raise RuntimeError(
                        f"ALPACA_DATA_HTTP_{exc.code}:{body}"
                    ) from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = RuntimeError(
                    f"ALPACA_DATA_NETWORK_ERROR:{type(exc).__name__}"
                )

            if attempt < self.config.maximum_attempts:
                self.sleep(self.config.backoff_seconds * attempt)

        raise last_error or RuntimeError("LATEST_TRADE_READ_FAILED")
