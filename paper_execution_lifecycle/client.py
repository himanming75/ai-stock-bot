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
            content = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ALPACA_HTTP_{exc.code}:{content}") from exc
        except URLError as exc:
            raise RuntimeError(f"ALPACA_NETWORK_ERROR:{exc.reason}") from exc

    def get_account(self) -> dict:
        result = self._get("/v2/account")
        return result if isinstance(result, dict) else {}

    def get_positions(self) -> list:
        result = self._get("/v2/positions")
        return result if isinstance(result, list) else []

    def get_orders(self, status: str = "all", limit: int = 500) -> list:
        result = self._get(
            f"/v2/orders?status={status}&limit={limit}&direction=desc&nested=true"
        )
        return result if isinstance(result, list) else []
