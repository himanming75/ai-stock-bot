from __future__ import annotations
from abc import ABC, abstractmethod
import json
import urllib.error
import urllib.request

from .credentials import AlpacaCredentials


class ReadOnlyTransport(ABC):
    @abstractmethod
    def get_json(self, path: str):
        raise NotImplementedError


class UrllibAlpacaReadOnlyTransport(ReadOnlyTransport):
    def __init__(self, credentials: AlpacaCredentials, timeout_seconds: int = 15) -> None:
        self.credentials = credentials
        self.timeout_seconds = timeout_seconds

    def get_json(self, path: str):
        if not path.startswith("/v2/"):
            raise ValueError("only /v2 read endpoints are allowed")
        request = urllib.request.Request(
            self.credentials.base_url + path,
            method="GET",
            headers={
                "APCA-API-KEY-ID": self.credentials.key_id,
                "APCA-API-SECRET-KEY": self.credentials.secret_key,
                "Accept": "application/json",
                "User-Agent": "ai-stock-bot-multi-broker-read-only",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Alpaca GET failed HTTP {exc.code}: {body[:300]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Alpaca GET network error: {exc}") from exc


class FixtureTransport(ReadOnlyTransport):
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.paths_requested: list[str] = []

    def get_json(self, path: str):
        self.paths_requested.append(path)
        if path not in self.responses:
            raise KeyError(f"fixture response missing for {path}")
        return self.responses[path]
