from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class AlpacaPaperCancelClient:
    PAPER_URL = "https://paper-api.alpaca.markets"
    DATA_URL = "https://data.alpaca.markets"

    def __init__(self) -> None:
        self.key = os.environ.get("APCA_API_KEY_ID", "").strip()
        self.secret = os.environ.get("APCA_API_SECRET_KEY", "").strip()
        self.trading_url = os.environ.get(
            "APCA_API_BASE_URL", self.PAPER_URL
        ).rstrip("/")
        self.data_url = os.environ.get(
            "APCA_API_DATA_URL", self.DATA_URL
        ).rstrip("/")

        if not self.key or not self.secret:
            raise RuntimeError("ALPACA_PAPER_CREDENTIALS_MISSING")
        if self.trading_url != self.PAPER_URL:
            raise RuntimeError("NON_PAPER_ENDPOINT_BLOCKED")

    def _request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> tuple[int, dict | None]:
        body = None
        headers = {
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Accept": "application/json",
            "User-Agent": "ai-stock-bot-p3-cancel-validation/1.0",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{base_url}{path}",
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            parsed = None
            if raw:
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = {"raw": raw}
            return exc.code, parsed

    def get_clock(self):
        status, payload = self._request(
            base_url=self.trading_url,
            method="GET",
            path="/v2/clock",
        )
        if status != 200:
            raise RuntimeError(f"CLOCK_READ_FAILED:{status}:{payload}")
        return payload

    def get_account(self):
        status, payload = self._request(
            base_url=self.trading_url,
            method="GET",
            path="/v2/account",
        )
        if status != 200:
            raise RuntimeError(f"ACCOUNT_READ_FAILED:{status}:{payload}")
        return payload

    def get_asset(self, symbol: str):
        status, payload = self._request(
            base_url=self.trading_url,
            method="GET",
            path=f"/v2/assets/{urllib.parse.quote(symbol)}",
        )
        if status != 200:
            raise RuntimeError(f"ASSET_READ_FAILED:{status}:{payload}")
        return payload

    def get_latest_trade(self, symbol: str):
        status, payload = self._request(
            base_url=self.data_url,
            method="GET",
            path=f"/v2/stocks/{urllib.parse.quote(symbol)}/trades/latest?feed=iex",
        )
        if status != 200:
            raise RuntimeError(f"LATEST_TRADE_FAILED:{status}:{payload}")
        return payload

    def submit_order(self, payload: dict):
        return self._request(
            base_url=self.trading_url,
            method="POST",
            path="/v2/orders",
            payload=payload,
        )

    def get_order(self, order_id: str):
        return self._request(
            base_url=self.trading_url,
            method="GET",
            path=f"/v2/orders/{urllib.parse.quote(order_id)}",
        )

    def get_order_by_client_id(self, client_order_id: str):
        query = urllib.parse.urlencode(
            {"client_order_id": client_order_id}
        )
        return self._request(
            base_url=self.trading_url,
            method="GET",
            path=f"/v2/orders:by_client_order_id?{query}",
        )

    def cancel_order(self, order_id: str):
        return self._request(
            base_url=self.trading_url,
            method="DELETE",
            path=f"/v2/orders/{urllib.parse.quote(order_id)}",
        )
