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

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers=self.headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Alpaca Paper HTTP {exc.code}: {raw}") from exc

    def account(self) -> dict:
        return self._request("GET", "/v2/account")

    def clock(self) -> dict:
        return self._request("GET", "/v2/clock")

    def open_orders(self) -> list:
        value = self._request("GET", "/v2/orders?status=open&direction=asc")
        return value if isinstance(value, list) else []

    def asset(self, symbol: str) -> dict:
        encoded = urllib.parse.quote(symbol, safe="")
        return self._request("GET", f"/v2/assets/{encoded}")

    def submit_order(self, payload: dict[str, Any]) -> dict:
        return self._request("POST", "/v2/orders", payload)

    def order_by_client_id(self, client_order_id: str) -> dict:
        query = urllib.parse.urlencode({"client_order_id": client_order_id})
        return self._request("GET", f"/v2/orders:by_client_order_id?{query}")
