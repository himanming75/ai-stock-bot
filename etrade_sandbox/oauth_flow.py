from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode

from .core import (
    ACCESS_TOKEN_URL,
    AUTHORIZE_URL,
    REQUEST_TOKEN_URL,
    RENEW_TOKEN_URL,
    REVOKE_TOKEN_URL,
    oauth_header,
)
from .transport import http_get


@dataclass(frozen=True)
class TokenPair:
    token: str
    secret: str


class ETradeOAuthFlow:
    def __init__(
        self,
        *,
        consumer_key: str,
        consumer_secret: str,
    ) -> None:
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

    def request_token(self) -> TokenPair:
        header = oauth_header(
            method="GET",
            url=REQUEST_TOKEN_URL,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            callback="oob",
        )
        result = http_get(
            url=REQUEST_TOKEN_URL,
            headers={
                "Authorization": header,
                "User-Agent": (
                    "AI-Stock-Bot-ETrade-Sandbox/1.0"
                ),
            },
        )
        values = parse_qs(
            result["body"].decode()
        )
        token = values.get("oauth_token", [""])[0]
        secret = values.get(
            "oauth_token_secret",
            [""],
        )[0]
        if not token or not secret:
            raise RuntimeError(
                "INVALID_REQUEST_TOKEN_RESPONSE"
            )
        return TokenPair(token, secret)

    def authorization_url(
        self,
        request_token: str,
    ) -> str:
        return (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "key": self.consumer_key,
                    "token": request_token,
                }
            )
        )

    def access_token(
        self,
        *,
        request_token: str,
        request_token_secret: str,
        verifier: str,
    ) -> TokenPair:
        header = oauth_header(
            method="GET",
            url=ACCESS_TOKEN_URL,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            token=request_token,
            token_secret=request_token_secret,
            verifier=verifier,
        )
        result = http_get(
            url=ACCESS_TOKEN_URL,
            headers={"Authorization": header},
        )
        values = parse_qs(
            result["body"].decode()
        )
        token = values.get("oauth_token", [""])[0]
        secret = values.get(
            "oauth_token_secret",
            [""],
        )[0]
        if not token or not secret:
            raise RuntimeError(
                "INVALID_ACCESS_TOKEN_RESPONSE"
            )
        return TokenPair(token, secret)

    def renew(
        self,
        *,
        access_token: str,
        access_token_secret: str,
    ) -> str:
        return self._token_action(
            url=RENEW_TOKEN_URL,
            access_token=access_token,
            access_token_secret=(
                access_token_secret
            ),
        )

    def revoke(
        self,
        *,
        access_token: str,
        access_token_secret: str,
    ) -> str:
        return self._token_action(
            url=REVOKE_TOKEN_URL,
            access_token=access_token,
            access_token_secret=(
                access_token_secret
            ),
        )

    def _token_action(
        self,
        *,
        url: str,
        access_token: str,
        access_token_secret: str,
    ) -> str:
        header = oauth_header(
            method="GET",
            url=url,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            token=access_token,
            token_secret=access_token_secret,
        )
        result = http_get(
            url=url,
            headers={"Authorization": header},
        )
        return result["body"].decode(
            "utf-8",
            errors="replace",
        )
