from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FillDeduplicationGuard:
    _seen: set[str] = None

    def __post_init__(self) -> None:
        if self._seen is None:
            self._seen = set()

    def register(self, fill_id: str) -> bool:
        if not fill_id:
            raise ValueError("fill_id is required")
        if fill_id in self._seen:
            return False
        self._seen.add(fill_id)
        return True
