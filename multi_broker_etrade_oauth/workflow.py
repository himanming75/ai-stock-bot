from __future__ import annotations
from datetime import datetime, timezone
import urllib.parse

from multi_broker_etrade.credentials import ETradeOAuthCredentials
from multi_broker_etrade.oauth import (
    hmac_sha1_signature,
    pct,
)
from .models import OAuthAccessToken, OAuthTemporaryToken
from .transport import OAuthTransport, parse_form_encoded


class ETradeOAuthWorkflow:
    REQUEST_TOKEN_URL = "https://api.etrade.com/oauth/request_token"
    AUTHORIZE_URL = "https://us.etrade.com/e/t/etws/authorize"
    ACCESS_TOKEN_URL = "https://api.etrade.com/oauth/access_token"
    RENEW_TOKEN_URL = "https://api.etrade.com/oauth/renew_access_token"
    REVOKE_TOKEN_URL = "https://api.etrade.com/oauth/revoke_access_token"

    def __init__(
        self,
        *,
        consumer_key: str,
        consumer_secret: str,
        transport: OAuthTransport,
    ) -> None:
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.transport = transport

    def _header(
        self,
        method: str,
        url: str,
        *,
        token: str = "",
        token_secret: str = "",
        verifier: str = "",
        callback: str = "oob",
        nonce: str = "fixture-nonce",
        timestamp: str = "1700000000",
    ) -> str:
        params = {
            "oauth_consumer_key": self.consumer_key,
            "oauth_nonce": nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_version": "1.0",
        }
        if token:
            params["oauth_token"] = token
        if verifier:
            params["oauth_verifier"] = verifier
        if callback:
            params["oauth_callback"] = callback

        params["oauth_signature"] = hmac_sha1_signature(
            method,
            url,
            params,
            self.consumer_secret,
            token_secret,
        )
        return "OAuth " + ",".join(
            f'{pct(key)}="{pct(value)}"'
            for key, value in sorted(params.items())
        )

    def request_token(self, callback: str = "oob") -> OAuthTemporaryToken:
        header = self._header(
            "GET",
            self.REQUEST_TOKEN_URL,
            callback=callback,
        )
        body = self.transport.post_form(
            self.REQUEST_TOKEN_URL,
            {"Authorization": header},
        )
        payload = parse_form_encoded(body)
        return OAuthTemporaryToken(
            oauth_token=payload["oauth_token"],
            oauth_token_secret=payload["oauth_token_secret"],
            callback_confirmed=(
                payload.get("oauth_callback_confirmed", "false").lower()
                == "true"
            ),
        )

    def authorization_url(self, request_token: OAuthTemporaryToken) -> str:
        return (
            self.AUTHORIZE_URL
            + "?key="
            + urllib.parse.quote(self.consumer_key)
            + "&token="
            + urllib.parse.quote(request_token.oauth_token)
        )

    def access_token(
        self,
        request_token: OAuthTemporaryToken,
        verifier: str,
        environment: str = "SANDBOX",
    ) -> OAuthAccessToken:
        header = self._header(
            "GET",
            self.ACCESS_TOKEN_URL,
            token=request_token.oauth_token,
            token_secret=request_token.oauth_token_secret,
            verifier=verifier,
            callback="",
        )
        body = self.transport.post_form(
            self.ACCESS_TOKEN_URL,
            {"Authorization": header},
        )
        payload = parse_form_encoded(body)
        return OAuthAccessToken(
            oauth_token=payload["oauth_token"],
            oauth_token_secret=payload["oauth_token_secret"],
            issued_at_utc=datetime.now(timezone.utc).isoformat(),
            environment=environment.upper(),
        )

    def renew(self, access_token: OAuthAccessToken) -> bool:
        header = self._header(
            "GET",
            self.RENEW_TOKEN_URL,
            token=access_token.oauth_token,
            token_secret=access_token.oauth_token_secret,
            callback="",
        )
        body = self.transport.post_form(
            self.RENEW_TOKEN_URL,
            {"Authorization": header},
        )
        payload = parse_form_encoded(body)
        return payload.get("oauth_token") == access_token.oauth_token

    def revoke(self, access_token: OAuthAccessToken) -> bool:
        header = self._header(
            "GET",
            self.REVOKE_TOKEN_URL,
            token=access_token.oauth_token,
            token_secret=access_token.oauth_token_secret,
            callback="",
        )
        body = self.transport.post_form(
            self.REVOKE_TOKEN_URL,
            {"Authorization": header},
        )
        payload = parse_form_encoded(body)
        return payload.get("revoked", "false").lower() == "true"
