from __future__ import annotations
from abc import ABC, abstractmethod
import urllib.parse


class OAuthTransport(ABC):
    @abstractmethod
    def post_form(self, url: str, headers: dict[str, str]) -> str:
        raise NotImplementedError


class FixtureOAuthTransport(OAuthTransport):
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def post_form(self, url: str, headers: dict[str, str]) -> str:
        self.calls.append({"url": url, "headers": dict(headers)})
        if url not in self.responses:
            raise KeyError(f"missing fixture OAuth response for {url}")
        return self.responses[url]


def parse_form_encoded(body: str) -> dict[str, str]:
    parsed = urllib.parse.parse_qs(body, keep_blank_values=True)
    return {
        key: values[-1]
        for key, values in parsed.items()
    }
