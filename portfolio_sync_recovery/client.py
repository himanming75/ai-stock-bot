from __future__ import annotations
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


PAPER_BASE_URL = "https://paper-api.alpaca.markets"


class AlpacaPaperReadClient:
    def __init__(self, api_key: str, secret_key: str, base_url: str = PAPER_BASE_URL):
        if base_url.rstrip("/") != PAPER_BASE_URL:
            raise ValueError("NON_PAPER_ENDPOINT_REJECTED")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.secret_key = secret_key

    def _get(self, path: str):
        req = Request(
            self.base_url + path,
            method="GET",
            headers={
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.secret_key,
            },
        )
        try:
            with urlopen(req, timeout=20) as response:
                content = response.read().decode("utf-8")
                return json.loads(content) if content else {}
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ALPACA_HTTP_{exc.code}:{body}") from exc
        except URLError as exc:
            raise RuntimeError(f"ALPACA_NETWORK_ERROR:{exc.reason}") from exc

    def get_account(self) -> dict:
        value = self._get("/v2/account")
        return value if isinstance(value, dict) else {}

    def get_positions(self) -> list:
        value = self._get("/v2/positions")
        return value if isinstance(value, list) else []

    def get_orders(self, status: str = "open") -> list:
        value = self._get(f"/v2/orders?status={status}&limit=500&direction=desc")
        return value if isinstance(value, list) else []
