from __future__ import annotations
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class OAuthTemporaryToken:
    oauth_token: str
    oauth_token_secret: str
    callback_confirmed: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OAuthAccessToken:
    oauth_token: str
    oauth_token_secret: str
    issued_at_utc: str
    environment: str

    def redacted(self) -> dict:
        return {
            "environment": self.environment,
            "issued_at_utc": self.issued_at_utc,
            "token_present": bool(self.oauth_token),
            "token_secret_present": bool(self.oauth_token_secret),
            "fingerprint": (
                f"{self.oauth_token[:4]}...{self.oauth_token[-4:]}"
                if len(self.oauth_token) >= 8 else "REDACTED"
            ),
        }


@dataclass(frozen=True)
class OAuthSessionState:
    status: str
    request_token_present: bool
    access_token_present: bool
    verification_code_consumed: bool
    renew_required: bool
    reauthorization_required: bool
    revoked: bool

    def to_dict(self) -> dict:
        return asdict(self)
