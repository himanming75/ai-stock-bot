from __future__ import annotations
import base64
import ctypes
import hashlib
import hmac
import json
import os
import secrets
import time
from ctypes import wintypes
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit


REQUEST_TOKEN_URL = "https://api.etrade.com/oauth/request_token"
ACCESS_TOKEN_URL = "https://api.etrade.com/oauth/access_token"
RENEW_TOKEN_URL = "https://api.etrade.com/oauth/renew_access_token"
REVOKE_TOKEN_URL = "https://api.etrade.com/oauth/revoke_access_token"
AUTHORIZE_URL = "https://us.etrade.com/e/t/etws/authorize"
SANDBOX_API_BASE = "https://apisb.etrade.com/v1"


def percent_encode(value: object) -> str:
    return quote(str(value), safe="~-._")


def normalized_url(url: str) -> str:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if port and not (
        (scheme == "https" and port == 443)
        or (scheme == "http" and port == 80)
    ):
        host = f"{host}:{port}"
    return urlunsplit(
        (scheme, host, parsed.path or "/", "", "")
    )


def oauth_header(
    *,
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: str = "",
    token_secret: str = "",
    callback: str | None = None,
    verifier: str | None = None,
    query: dict[str, object] | None = None,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> str:
    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce or secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(
            timestamp if timestamp is not None else int(time.time())
        ),
        "oauth_version": "1.0",
    }
    if token:
        oauth["oauth_token"] = token
    if callback is not None:
        oauth["oauth_callback"] = callback
    if verifier is not None:
        oauth["oauth_verifier"] = verifier

    params = list(oauth.items())
    params += parse_qsl(
        urlsplit(url).query,
        keep_blank_values=True,
    )
    params += [
        (str(k), str(v))
        for k, v in (query or {}).items()
        if v is not None
    ]
    encoded = sorted(
        (percent_encode(k), percent_encode(v))
        for k, v in params
    )
    normalized_params = "&".join(
        f"{k}={v}" for k, v in encoded
    )
    base = "&".join(
        (
            percent_encode(method.upper()),
            percent_encode(normalized_url(url)),
            percent_encode(normalized_params),
        )
    )
    signing_key = (
        f"{percent_encode(consumer_secret)}&"
        f"{percent_encode(token_secret)}"
    )
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode(),
            base.encode(),
            hashlib.sha1,
        ).digest()
    ).decode()
    oauth["oauth_signature"] = signature
    rendered = ", ".join(
        f'{percent_encode(k)}="{percent_encode(v)}"'
        for k, v in sorted(oauth.items())
    )
    return f"OAuth {rendered}"


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(
        len(data),
        ctypes.cast(
            buffer,
            ctypes.POINTER(ctypes.c_byte),
        ),
    )
    return blob, buffer


def dpapi_protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("WINDOWS_DPAPI_REQUIRED")
    input_blob, keepalive = _blob(data)
    output_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "AI Stock Bot ETrade Sandbox",
        None, None, None, 0x01,
        ctypes.byref(output_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(
            output_blob.pbData,
            output_blob.cbData,
        )
    finally:
        ctypes.windll.kernel32.LocalFree(
            output_blob.pbData
        )


def dpapi_unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("WINDOWS_DPAPI_REQUIRED")
    input_blob, keepalive = _blob(data)
    output_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None, None, None, None, 0x01,
        ctypes.byref(output_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(
            output_blob.pbData,
            output_blob.cbData,
        )
    finally:
        ctypes.windll.kernel32.LocalFree(
            output_blob.pbData
        )


class ETradeCredentialVault:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, data: dict) -> None:
        if not data.get("consumer_key"):
            raise ValueError("MISSING_CONSUMER_KEY")
        if not data.get("consumer_secret"):
            raise ValueError("MISSING_CONSUMER_SECRET")
        raw = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        protected = dpapi_protect(raw)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.path.write_text(
            json.dumps(
                {
                    "format": "WINDOWS_DPAPI_V1",
                    "ciphertext": base64.b64encode(
                        protected
                    ).decode(),
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

    def load(self) -> dict:
        wrapper = json.loads(
            self.path.read_text(encoding="utf-8")
        )
        if wrapper.get("format") != "WINDOWS_DPAPI_V1":
            raise ValueError("INVALID_VAULT_FORMAT")
        raw = dpapi_unprotect(
            base64.b64decode(
                wrapper["ciphertext"]
            )
        )
        return json.loads(raw.decode())

    def exists(self) -> bool:
        return self.path.exists()
