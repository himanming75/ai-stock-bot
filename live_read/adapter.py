from __future__ import annotations
from typing import Any

from .http_guard import GetOnlyHttpGuard
from . import normalizers


class AlpacaLiveReadAdapter:
    def __init__(self, client: GetOnlyHttpGuard) -> None:
        self.client = client

    def get_account(self) -> dict[str, Any]:
        return normalizers.account(
            self.client.request_json("GET", "/v2/account")
        )

    def get_positions(self) -> list[dict[str, Any]]:
        return normalizers.positions(
            self.client.request_json("GET", "/v2/positions")
        )

    def get_open_orders(self) -> list[dict[str, Any]]:
        return normalizers.orders(
            self.client.request_json(
                "GET",
                "/v2/orders?status=open&direction=asc",
            )
        )

    def get_clock(self) -> dict[str, Any]:
        return normalizers.clock(
            self.client.request_json("GET", "/v2/clock")
        )

    def get_asset(self, symbol: str) -> dict[str, Any]:
        normalized = symbol.strip().upper()
        if not normalized or not normalized.replace(".", "").isalnum():
            raise ValueError("INVALID_ASSET_SYMBOL")
        return normalizers.asset(
            self.client.request_json(
                "GET",
                f"/v2/assets/{normalized}",
            )
        )
