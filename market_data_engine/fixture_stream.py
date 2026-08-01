from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .parser import AlpacaMessageParser
from .router import MarketDataRouter


class FixtureMarketDataStream:
    """Offline deterministic stream used for tests and local runtime demos."""

    def __init__(self, *, frames: Iterable[Any], parser: AlpacaMessageParser, router: MarketDataRouter):
        self.frames = list(frames)
        self.parser = parser
        self.router = router
        self.frame_count = 0
        self.message_count = 0

    def run(self) -> dict[str, int]:
        for frame in self.frames:
            self.frame_count += 1
            for message in self.parser.parse_frame(frame):
                self.message_count += 1
                self.router.route(message)
        return {
            "frame_count": self.frame_count,
            "message_count": self.message_count,
            "published_count": self.router.stats.published,
        }
