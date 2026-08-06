from __future__ import annotations
from typing import Any

from .core import (
    SANDBOX_API_BASE,
    oauth_header,
)
from .transport import http_get, response_json


BLOCKED = (
    "/orders/place",
    "/orders/preview",
    "/orders/cancel",
    "/change/preview",
    "/change/place",
)


class ETradeSandboxReadOnlyClient:
    def __init__(
        self,
        *,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
    ) -> None:
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = (
            access_token_secret
        )

    def _get(
        self,
        path: str,
        *,
        query: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        path = "/" + path.lstrip("/")
        if any(
            item in path.lower()
            for item in BLOCKED
        ):
            raise PermissionError(
                "ETRADE_WRITE_ENDPOINT_BLOCKED"
            )
        url = SANDBOX_API_BASE + path
        header = oauth_header(
            method="GET",
            url=url,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            token=self.access_token,
            token_secret=self.access_token_secret,
            query=query,
        )
        result = http_get(
            url=url,
            query=query,
            headers={
                "Authorization": header,
                "Accept": "application/json",
                "User-Agent": (
                    "AI-Stock-Bot-ETrade-Sandbox/"
                    "ReadOnly-1.0"
                ),
            },
        )
        data = (
            None
            if result["status_code"] == 204
            else response_json(result)
        )
        return {
            "status_code": result["status_code"],
            "elapsed_ms": result["elapsed_ms"],
            "data": data,
        }

    def list_accounts(self) -> dict:
        return self._get(
            "/accounts/list.json"
        )

    def balance(
        self,
        account_id_key: str,
    ) -> dict:
        return self._get(
            f"/accounts/{account_id_key}/balance.json",
            query={
                "instType": "BROKERAGE",
                "realTimeNAV": "true",
            },
        )

    def portfolio(
        self,
        account_id_key: str,
    ) -> dict:
        return self._get(
            f"/accounts/{account_id_key}/portfolio.json",
            query={
                "count": 50,
                "view": "COMPLETE",
                "totalsRequired": "true",
            },
        )

    def orders(
        self,
        account_id_key: str,
    ) -> dict:
        return self._get(
            f"/accounts/{account_id_key}/orders.json",
            query={"count": 100},
        )

    def quote(
        self,
        symbols: list[str],
    ) -> dict:
        clean = [
            item.strip().upper()
            for item in symbols
            if item.strip()
        ]
        if not clean:
            raise ValueError("SYMBOL_REQUIRED")
        if len(clean) > 25:
            raise ValueError("MAXIMUM_25_SYMBOLS")
        return self._get(
            "/market/quote/"
            + ",".join(clean)
            + ".json",
            query={
                "detailFlag": "ALL",
                "requireEarningsDate": "false",
                "skipMiniOptionsCheck": "true",
            },
        )

    def write_request(self, *args, **kwargs):
        raise PermissionError(
            "ETRADE_WRITE_DISABLED"
        )
