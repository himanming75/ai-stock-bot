from __future__ import annotations
from dataclasses import dataclass
import hashlib
import os


@dataclass(frozen=True)
class AlpacaCredentials:
    key_id: str
    secret_key: str
    base_url: str = "https://paper-api.alpaca.markets"

    def fingerprint(self) -> str:
        seed = f"{self.key_id}|{self.base_url}".encode("utf-8")
        return hashlib.sha256(seed).hexdigest()[:16]


class EnvironmentAlpacaCredentialProvider:
    KEY_NAMES = ("APCA_API_KEY_ID", "ALPACA_API_KEY")
    SECRET_NAMES = ("APCA_API_SECRET_KEY", "ALPACA_SECRET_KEY")
    BASE_URL_NAMES = ("APCA_API_BASE_URL", "ALPACA_BASE_URL")

    @staticmethod
    def _first(names: tuple[str, ...]) -> str:
        for name in names:
            value = os.environ.get(name, "").strip()
            if value:
                return value
        return ""

    def load(self) -> AlpacaCredentials:
        key_id = self._first(self.KEY_NAMES)
        secret_key = self._first(self.SECRET_NAMES)
        base_url = self._first(self.BASE_URL_NAMES) or "https://paper-api.alpaca.markets"
        if not key_id or not secret_key:
            raise RuntimeError("Alpaca credentials are not configured in environment variables")
        if "paper-api.alpaca.markets" not in base_url:
            raise RuntimeError("Only Alpaca paper endpoint is allowed in this stage")
        return AlpacaCredentials(
            key_id=key_id,
            secret_key=secret_key,
            base_url=base_url.rstrip("/"),
        )
