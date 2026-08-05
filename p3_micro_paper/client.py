from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


class AlpacaPaperTradingClient:
    PAPER_URL = "https://paper-api.alpaca.markets"

    def __init__(self) -> None:
        self.key = os.environ.get("APCA_API_KEY_ID", "").strip()
        self.secret = os.environ.get("APCA_API_SECRET_KEY", "").strip()
        self.base_url = os.environ.get(
            "APCA_API_BASE_URL", self.PAPER_URL
        ).rstrip("/")

        if not self.key or not self.secret:
            raise RuntimeError("ALPACA_PAPER_CREDENTIALS_MISSING")
        if self.base_url != self.PAPER_URL:
            raise RuntimeError("NON_PAPER_ENDPOINT_BLOCKED")

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ):
        data = None
        headers = {
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Accept": "application/json",
            "User-Agent": "ai-stock-bot-p3-micro-paper-validation/1.0",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    def get_clock(self):
        return self._request("GET", "/v2/clock")

    def get_account(self):
        return self._request("GET", "/v2/account")

    def get_asset(self, symbol: str):
        encoded = urllib.parse.quote(symbol)
        return self._request("GET", f"/v2/assets/{encoded}")

    def get_order_by_client_id(self, client_order_id: str):
        query = urllib.parse.urlencode(
            {"client_order_id": client_order_id}
        )
        return self._request(
            "GET",
            f"/v2/orders:by_client_order_id?{query}",
        )

    def submit_order(self, payload: dict):
        return self._request("POST", "/v2/orders", payload)
