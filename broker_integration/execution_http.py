from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from .execution_config import ExecutionConfig


class AlpacaPaperExecutionHttp:
    def __init__(
        self,
        config: ExecutionConfig,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.opener = opener
        self.sleep = sleep

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.config.api_key,
            "APCA-API-SECRET-KEY": self.config.secret_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ai-stock-bot-p2-paper-execution",
        }

    def request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[Any, str]:
        if not self.config.paper_endpoint_enforced:
            raise PermissionError("PAPER_ENDPOINT_NOT_ENFORCED")
        if not self.config.credentials_present:
            raise PermissionError("PAPER_CREDENTIALS_MISSING")
        if not self.config.network_enabled:
            raise PermissionError("PAPER_EXECUTION_NETWORK_DISABLED")
        if method.upper() != "GET":
            if not self.config.write_enabled:
                raise PermissionError("PAPER_EXECUTION_WRITE_DISABLED")
            if not self.config.explicit_confirmation_valid:
                raise PermissionError("PAPER_EXECUTION_CONFIRMATION_INVALID")

        data = (
            json.dumps(payload).encode("utf-8")
            if payload is not None
            else None
        )
        request = urllib.request.Request(
            url=f"{self.config.base_url}{path}",
            data=data,
            headers=self._headers(),
            method=method.upper(),
        )

        last_error: Exception | None = None
        for attempt in range(1, self.config.maximum_attempts + 1):
            try:
                with self.opener(
                    request,
                    timeout=self.config.timeout_seconds,
                ) as response:
                    body = response.read().decode("utf-8")
                    request_id = response.headers.get("X-Request-ID", "")
                    return json.loads(body), request_id
            except urllib.error.HTTPError as exc:
                response_body = ""
                try:
                    response_body = exc.read().decode("utf-8")
                except Exception:
                    pass
                if exc.code in {400, 401, 403, 404, 422}:
                    raise RuntimeError(
                        f"ALPACA_HTTP_{exc.code}:{response_body}"
                    ) from exc
                if exc.code == 429 or 500 <= exc.code <= 599:
                    last_error = RuntimeError(
                        f"ALPACA_RETRYABLE_HTTP_{exc.code}:{response_body}"
                    )
                else:
                    raise RuntimeError(
                        f"ALPACA_HTTP_{exc.code}:{response_body}"
                    ) from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = RuntimeError(
                    f"ALPACA_NETWORK_ERROR:{type(exc).__name__}"
                )

            if attempt < self.config.maximum_attempts:
                self.sleep(self.config.backoff_seconds * attempt)

        raise last_error or RuntimeError("ALPACA_EXECUTION_REQUEST_FAILED")

    def submit_order(
        self,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        value, request_id = self.request_json("POST", "/v2/orders", payload)
        return value, request_id

    def cancel_order(self, order_id: str) -> tuple[dict[str, Any], str]:
        value, request_id = self.request_json(
            "DELETE",
            f"/v2/orders/{order_id}",
        )
        return value if isinstance(value, dict) else {}, request_id

    def replace_order(
        self,
        order_id: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        value, request_id = self.request_json(
            "PATCH",
            f"/v2/orders/{order_id}",
            payload,
        )
        return value, request_id
