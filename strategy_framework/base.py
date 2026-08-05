from __future__ import annotations

from abc import ABC, abstractmethod


class Strategy(ABC):
    name = "base"
    minimum_bars = 2

    @abstractmethod
    def evaluate(self, symbol: str, bars: list[dict], config: dict) -> dict:
        raise NotImplementedError
