from __future__ import annotations

import argparse
import json
import os

from .etrade_oauth_flow_v2 import (
    ETradeOAuthFlow,
    ETradeOAuthHTTPError,
    ETradeOAuthTransportError,
)
from .etrade_oauth_profile_v2 import ETRADE_OAUTH_PROFILE


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--network",action="store_true")
    a=p.parse_args()

    print("E*TRADE OAUTH HTTP DIAGNOSTIC V2.1.2.1")
    print("Network enabled:",bool(a.network))
    print(
        "Request-token endpoint:",
        ETRADE_OAUTH_PROFILE["request_token_url"],
    )
    print(
        "Access-token endpoint:",
        ETRADE_OAUTH_PROFILE["access_token_url"],
    )
    print("Credentials printed: NO")
    print("OAuth tokens printed: NO")
    print("PROD orders: LOCKED")

    key=os.environ.get("ETRADE_CONSUMER_KEY")
    secret=os.environ.get("ETRADE_CONSUMER_SECRET")

    print("Consumer key present:",bool(key))
    print("Consumer secret present:",bool(secret))

    if not key or not secret:
        print("STATUS: WAITING_FOR_CREDENTIALS")
        return 3

    if not a.network:
        print("STATUS: NETWORK_NOT_ENABLED")
        return 4

    flow=ETradeOAuthFlow(
        key,
        secret,
        network_enabled=True,
        callback="oob",
    )

    try:
        result=flow.request_token()
    except ETradeOAuthHTTPError as exc:
        print("")
        print("=== OAUTH REQUEST TOKEN FAILED ===")
        print("HTTP STATUS:",exc.status)
        print("ENDPOINT:",exc.url)
        print("SAFE RESPONSE HEADERS:")
        print(
            json.dumps(
                exc.safe_headers,
                indent=2,
                ensure_ascii=False,
            )
        )
        print("RESPONSE BODY:")
        print(exc.response_body)
        print("")
        print("Credential values: NOT DISPLAYED")
        print("OAuth token values: NOT DISPLAYED")
        print("PROD orders: LOCKED")
        return 10
    except ETradeOAuthTransportError as exc:
        print("TRANSPORT ERROR:",str(exc))
        return 11

    print("")
    print("REQUEST TOKEN HTTP: PASS")
    print("oauth_token present:",bool(result.get("oauth_token")))
    print(
        "oauth_token_secret present:",
        bool(result.get("oauth_token_secret")),
    )
    print(
        "oauth_callback_confirmed:",
        result.get("oauth_callback_confirmed"),
    )
    print("Token values: NOT DISPLAYED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
