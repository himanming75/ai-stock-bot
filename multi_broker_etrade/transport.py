from __future__ import annotations
from abc import ABC, abstractmethod
import json
import urllib.error
import urllib.request

from .credentials import ETradeOAuthCredentials
from .oauth import build_oauth_header


class ETradeReadOnlyTransport(ABC):
    @abstractmethod
    def get_json(self, path: str):
        raise NotImplementedError


class UrllibETradeOAuthTransport(ETradeReadOnlyTransport):
    ALLOWED_PREFIXES = (
        "/v1/accounts/list",
        "/v1/accounts/",
    )

    def __init__(self, credentials: ETradeOAuthCredentials, timeout_seconds: int = 15):
        self.credentials = credentials
        self.timeout_seconds = timeout_seconds

    def get_json(self, path: str):
        if not path.startswith(self.ALLOWED_PREFIXES):
            raise PermissionError(f"E*TRADE read endpoint not allowed: {path}")
        if any(fragment in path.lower() for fragment in ("/place", "/preview", "/cancel")):
            raise PermissionError("E*TRADE order mutation endpoint blocked")
        url = self.credentials.base_url + path
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": build_oauth_header(
                    self.credentials,
                    "GET",
                    url,
                ),
                "Accept": "application/json",
                "User-Agent": "ai-stock-bot-etrade-read-only",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"E*TRADE GET failed HTTP {exc.code}: {body[:300]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"E*TRADE GET network error: {exc}") from exc


class FixtureTransport(ETradeReadOnlyTransport):
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.paths_requested: list[str] = []

    def get_json(self, path: str):
        self.paths_requested.append(path)
        if path not in self.responses:
            raise KeyError(f"fixture response missing for {path}")
        return self.responses[path]
