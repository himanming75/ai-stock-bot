from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import AlpacaHttpError, AlpacaResponseError
from .models import BrokerResponse


class HttpTransport(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        timeout_seconds: float,
        body: dict[str, object] | None = None,
        max_retries: int = 0,
    ) -> BrokerResponse:
        ...


@dataclass
class UrllibHttpTransport:
    sleep: object = time.sleep
    opener: object = urlopen

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        timeout_seconds: float,
        body: dict[str, object] | None = None,
        max_retries: int = 0,
    ) -> BrokerResponse:
        encoded = None
        request_headers = dict(headers)
        if body is not None:
            encoded = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"

        attempts = 0
        while True:
            attempts += 1
            request = Request(
                url=url,
                data=encoded,
                headers=request_headers,
                method=method.upper(),
            )
            try:
                with self.opener(request, timeout=timeout_seconds) as response:
                    raw = response.read()
                    payload = None
                    if raw:
                        try:
                            payload = json.loads(raw.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                            raise AlpacaResponseError("invalid JSON response") from exc
                    return BrokerResponse(
                        status_code=int(response.status),
                        payload=payload,
                        request_id=response.headers.get("X-Request-ID"),
                        attempts=attempts,
                    )
            except HTTPError as exc:
                request_id = exc.headers.get("X-Request-ID") if exc.headers else None
                raw = exc.read().decode("utf-8", errors="replace")
                retryable = exc.code in {429, 500, 502, 503, 504}
                if retryable and attempts <= max_retries:
                    self.sleep(min(attempts, 2))
                    continue
                raise AlpacaHttpError(exc.code, raw or str(exc), request_id) from exc
            except URLError as exc:
                if attempts <= max_retries:
                    self.sleep(min(attempts, 2))
                    continue
                raise AlpacaHttpError(0, f"network error: {exc.reason}") from exc
