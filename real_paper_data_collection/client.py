from __future__ import annotations
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

class AlpacaPaperClient:
    def __init__(self, key: str, secret: str, base_url: str) -> None:
        if base_url != "https://paper-api.alpaca.markets":
            raise ValueError("Only Alpaca Paper endpoint is allowed.")
        self.base_url = base_url
        self.headers = {
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Content-Type": "application/json",
        }

    def _request(self, path: str) -> Any:
        request = urllib.request.Request(
            self.base_url + path,
            headers=self.headers,
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Alpaca Paper HTTP {error.code}: {raw}") from error

    def account(self) -> dict:
        value = self._request("/v2/account")
        return value if isinstance(value, dict) else {}

    def clock(self) -> dict:
        value = self._request("/v2/clock")
        return value if isinstance(value, dict) else {}

    def positions(self) -> list:
        value = self._request("/v2/positions")
        return value if isinstance(value, list) else []

    def orders(self, status: str, limit: int = 100) -> list:
        query = urllib.parse.urlencode({
            "status": status,
            "direction": "desc",
            "limit": limit,
            "nested": "true",
        })
        value = self._request(f"/v2/orders?{query}")
        return value if isinstance(value, list) else []
