from __future__ import annotations
from typing import Any

from .http_client import ReadOnlyHttpClient
from . import normalizers


class AlpacaPaperReadAdapter:
    def __init__(self, client: ReadOnlyHttpClient) -> None:
        self.client = client

    def get_account(self) -> dict[str, Any]:
        return normalizers.account(self.client.get_json("/v2/account"))

    def get_positions(self) -> list[dict[str, Any]]:
        return normalizers.positions(self.client.get_json("/v2/positions"))

    def get_open_orders(self) -> list[dict[str, Any]]:
        return normalizers.orders(
            self.client.get_json("/v2/orders?status=open&direction=asc")
        )

    def get_clock(self) -> dict[str, Any]:
        return normalizers.clock(self.client.get_json("/v2/clock"))

    def get_asset(self, symbol: str) -> dict[str, Any]:
        normalized = symbol.strip().upper()
        if not normalized or not normalized.replace(".", "").isalnum():
            raise ValueError("INVALID_ASSET_SYMBOL")
        return normalizers.asset(
            self.client.get_json(f"/v2/assets/{normalized}")
        )
