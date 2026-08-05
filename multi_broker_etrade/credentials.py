from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os


@dataclass(frozen=True)
class ETradeOAuthCredentials:
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_secret: str
    environment: str = "SANDBOX"
    issued_at_utc: str | None = None

    @property
    def base_url(self) -> str:
        return (
            "https://apisb.etrade.com"
            if self.environment.upper() == "SANDBOX"
            else "https://api.etrade.com"
        )

    def fingerprint(self) -> str:
        seed = f"{self.consumer_key}|{self.access_token}|{self.environment}".encode("utf-8")
        return hashlib.sha256(seed).hexdigest()[:16]

    def redacted(self) -> dict:
        return {
            "environment": self.environment.upper(),
            "base_url": self.base_url,
            "fingerprint": self.fingerprint(),
            "issued_at_utc": self.issued_at_utc,
            "consumer_key_present": bool(self.consumer_key),
            "consumer_secret_present": bool(self.consumer_secret),
            "access_token_present": bool(self.access_token),
            "access_secret_present": bool(self.access_secret),
        }


class EnvironmentETradeCredentialProvider:
    def load(self) -> ETradeOAuthCredentials:
        environment = os.environ.get("ETRADE_ENVIRONMENT", "SANDBOX").strip().upper()
        if environment not in {"SANDBOX", "PRODUCTION"}:
            raise RuntimeError("ETRADE_ENVIRONMENT must be SANDBOX or PRODUCTION")

        values = {
            "consumer_key": os.environ.get("ETRADE_CONSUMER_KEY", "").strip(),
            "consumer_secret": os.environ.get("ETRADE_CONSUMER_SECRET", "").strip(),
            "access_token": os.environ.get("ETRADE_ACCESS_TOKEN", "").strip(),
            "access_secret": os.environ.get("ETRADE_ACCESS_SECRET", "").strip(),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise RuntimeError("Missing E*TRADE credentials: " + ", ".join(missing))

        if environment == "PRODUCTION":
            allow = os.environ.get("ETRADE_ALLOW_PRODUCTION_READ", "").strip().upper()
            if allow != "YES":
                raise RuntimeError(
                    "Production read access is blocked unless "
                    "ETRADE_ALLOW_PRODUCTION_READ=YES"
                )

        return ETradeOAuthCredentials(
            **values,
            environment=environment,
            issued_at_utc=os.environ.get(
                "ETRADE_ACCESS_TOKEN_ISSUED_AT_UTC",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
