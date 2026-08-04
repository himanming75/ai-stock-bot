from __future__ import annotations
import json
import urllib.error
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

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers=self.headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Alpaca Paper HTTP {error.code}: {raw}") from error

    def account(self) -> dict:
        return self._request("GET", "/v2/account")

    def clock(self) -> dict:
        return self._request("GET", "/v2/clock")

    def positions(self) -> list:
        value = self._request("GET", "/v2/positions")
        return value if isinstance(value, list) else []

    def open_orders(self) -> list:
        value = self._request("GET", "/v2/orders?status=open&direction=asc")
        return value if isinstance(value, list) else []

    def submit_order(self, plan: dict) -> dict:
        payload = {
            "symbol": plan["symbol"],
            "qty": str(plan["quantity"]),
            "side": plan["action"].lower(),
            "type": plan["order_type"].lower(),
            "time_in_force": plan["time_in_force"].lower(),
            "client_order_id": plan["client_order_id"],
        }
        if plan["order_type"].upper() == "LIMIT":
            payload["limit_price"] = str(plan["limit_price"])
        return self._request("POST", "/v2/orders", payload)
