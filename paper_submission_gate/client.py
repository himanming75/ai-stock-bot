from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


class AlpacaPaperClient:
    def __init__(self) -> None:
        self.key = os.environ.get("APCA_API_KEY_ID", "").strip()
        self.secret = os.environ.get("APCA_API_SECRET_KEY", "").strip()
        self.base = os.environ.get(
            "APCA_API_BASE_URL", "https://paper-api.alpaca.markets"
        ).rstrip("/")

        if not self.key or not self.secret:
            raise RuntimeError("ALPACA_PAPER_CREDENTIALS_MISSING")
        if self.base != "https://paper-api.alpaca.markets":
            raise RuntimeError("NON_PAPER_ENDPOINT_BLOCKED")

    def _request(self, method: str, path: str, payload: dict | None = None):
        body = None
        headers = {
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Accept": "application/json",
            "User-Agent": "ai-stock-bot-paper-submission-gate/1.0",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{self.base}{path}",
            data=body,
            method=method,
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def clock(self):
        return self._request("GET", "/v2/clock")

    def account(self):
        return self._request("GET", "/v2/account")

    def open_orders(self):
        return self._request("GET", "/v2/orders?status=open&limit=100")

    def submit_order(self, payload: dict):
        return self._request("POST", "/v2/orders", payload)

    def get_order_by_client_order_id(self, client_order_id: str):
        query = urllib.parse.urlencode({"client_order_id": client_order_id})
        return self._request("GET", f"/v2/orders:by_client_order_id?{query}")

    def cancel_order(self, broker_order_id: str):
        return self._request("DELETE", f"/v2/orders/{broker_order_id}")
