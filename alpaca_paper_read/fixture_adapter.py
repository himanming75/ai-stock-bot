from __future__ import annotations
from copy import deepcopy
from typing import Any


class FixtureReadAdapter:
    def __init__(self, fixture: dict[str, Any]) -> None:
        self.fixture = deepcopy(fixture)

    def get_account(self) -> dict[str, Any]:
        return deepcopy(self.fixture["account"])

    def get_positions(self) -> list[dict[str, Any]]:
        return deepcopy(self.fixture["positions"])

    def get_open_orders(self) -> list[dict[str, Any]]:
        return deepcopy(self.fixture["open_orders"])

    def get_clock(self) -> dict[str, Any]:
        return deepcopy(self.fixture["clock"])

    def get_asset(self, symbol: str) -> dict[str, Any]:
        normalized = symbol.strip().upper()
        assets = self.fixture.get("assets", {})
        if normalized not in assets:
            raise KeyError(f"ASSET_NOT_FOUND:{normalized}")
        return deepcopy(assets[normalized])
