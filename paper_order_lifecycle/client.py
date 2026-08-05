from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


class AlpacaPaperReadClient:
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

    def _get(self, path: str):
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            method="GET",
            headers={
                "APCA-API-KEY-ID": self.key,
                "APCA-API-SECRET-KEY": self.secret,
                "Accept": "application/json",
                "User-Agent": "ai-stock-bot-paper-lifecycle-monitor/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    def get_order_by_client_id(self, client_order_id: str):
        query = urllib.parse.urlencode(
            {"client_order_id": client_order_id}
        )
        return self._get(
            f"/v2/orders:by_client_order_id?{query}"
        )

    def get_account(self):
        return self._get("/v2/account")

    def get_positions(self):
        return self._get("/v2/positions")

    def get_clock(self):
        return self._get("/v2/clock")
