from __future__ import annotations
import base64
import hashlib
import hmac
import time
import urllib.parse
import uuid

from .credentials import ETradeOAuthCredentials


def pct(value: str) -> str:
    return urllib.parse.quote(str(value), safe="~-._")


def normalized_parameter_string(parameters: dict[str, str]) -> str:
    return "&".join(
        f"{pct(key)}={pct(value)}"
        for key, value in sorted(parameters.items())
    )


def signature_base_string(method: str, url: str, parameters: dict[str, str]) -> str:
    return "&".join(
        [
            method.upper(),
            pct(url),
            pct(normalized_parameter_string(parameters)),
        ]
    )


def hmac_sha1_signature(
    method: str,
    url: str,
    oauth_parameters: dict[str, str],
    consumer_secret: str,
    token_secret: str,
) -> str:
    base = signature_base_string(method, url, oauth_parameters)
    signing_key = f"{pct(consumer_secret)}&{pct(token_secret)}"
    digest = hmac.new(
        signing_key.encode("utf-8"),
        base.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def build_oauth_header(
    credentials: ETradeOAuthCredentials,
    method: str,
    url: str,
    *,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> str:
    parameters = {
        "oauth_consumer_key": credentials.consumer_key,
        "oauth_nonce": nonce or uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(timestamp or int(time.time())),
        "oauth_token": credentials.access_token,
        "oauth_version": "1.0",
    }
    parameters["oauth_signature"] = hmac_sha1_signature(
        method,
        url,
        parameters,
        credentials.consumer_secret,
        credentials.access_secret,
    )
    rendered = ",".join(
        f'{pct(key)}="{pct(value)}"'
        for key, value in sorted(parameters.items())
    )
    return "OAuth " + rendered
