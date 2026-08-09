from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import webbrowser

from .etrade_oauth_flow_v2 import ETradeOAuthFlow
from .etrade_readonly_connection_v2 import ETradeReadOnlyConnection


def _safe_account(row):
    return {
        "account_id_key": row.get("accountIdKey"),
        "account_desc": row.get("accountDesc"),
        "account_mode": row.get("accountMode"),
        "account_type": row.get("accountType"),
    }


def _write_redacted_snapshot(root, payload):
    path=Path(root)/"runtime"/"etrade_readonly_v2"/"latest_readonly_snapshot.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    return path


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--environment",choices=["sandbox","production"],default="sandbox")
    p.add_argument("--network",action="store_true")
    p.add_argument("--no-browser",action="store_true")
    p.add_argument("--account-id-key")
    p.add_argument("--revoke-after",action="store_true")
    a=p.parse_args()

    key=os.environ.get("ETRADE_CONSUMER_KEY")
    secret=os.environ.get("ETRADE_CONSUMER_SECRET")

    print("E*TRADE READ-ONLY OAUTH V2")
    print("Environment:",a.environment)
    print("Network enabled:",bool(a.network))
    print("Consumer key present:",bool(key))
    print("Consumer secret present:",bool(secret))
    print("Token persistence: DISABLED")
    print("Order submission: LOCKED")
    print("Cancel/replace: LOCKED")
    print("Live trading: LOCKED")

    if not key or not secret:
        print("STATUS: WAITING_FOR_CREDENTIALS")
        return 3

    if not a.network:
        print("STATUS: READY_BUT_NETWORK_NOT_ENABLED")
        return 4

    flow=ETradeOAuthFlow(key,secret,network_enabled=True,callback="oob")
    request=flow.request_token()
    request_token=request.get("oauth_token")
    request_secret=request.get("oauth_token_secret")
    if not request_token or not request_secret:
        raise RuntimeError("E*TRADE request token response did not include token and secret.")

    url=flow.authorization_url(request_token)
    print("Authorization URL:",url)
    if not a.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    verifier=input("Paste E*TRADE verification code: ").strip()
    if not verifier:
        raise RuntimeError("Verification code is required.")

    access=flow.access_token(request_token,request_secret,verifier)
    access_token=access.get("oauth_token")
    access_secret=access.get("oauth_token_secret")
    if not access_token or not access_secret:
        raise RuntimeError("E*TRADE access token response did not include token and secret.")

    conn=ETradeReadOnlyConnection(
        key,secret,access_token,access_secret,
        environment=a.environment,network_enabled=True,
    )

    accounts=conn.list_accounts()
    result={
        "status":"PASS_READONLY_ACCOUNT_CONNECTION",
        "environment":a.environment,
        "account_count":len(accounts),
        "accounts":[_safe_account(row) for row in accounts],
        "token_values_persisted":False,
        "order_submission":"LOCKED",
        "cancel_replace":"LOCKED",
        "live_trading":"LOCKED",
    }

    if a.account_id_key:
        snap=conn.snapshot(a.account_id_key)
        result["snapshot"]={
            "account_id_masked":snap.account_id_masked,
            "currency":snap.currency,
            "cash":str(snap.cash),
            "buying_power":str(snap.buying_power),
            "equity":str(snap.equity),
            "position_count":len(snap.positions),
            "positions":[
                {
                    "symbol":p.symbol,
                    "quantity":str(p.quantity),
                    "market_value":str(p.market_value),
                    "unrealized_pnl":str(p.unrealized_pnl),
                }
                for p in snap.positions
            ],
            "open_order_count":len(snap.open_orders),
        }

    path=_write_redacted_snapshot(a.root,result)
    print(json.dumps(result,indent=2))
    print("Redacted snapshot:",path)
    print("Access token values: NOT DISPLAYED / NOT PERSISTED")

    if a.revoke_after:
        flow.revoke(access_token,access_secret)
        print("OAuth access token revoke: REQUESTED")

    return 0


if __name__=="__main__":
    raise SystemExit(main())
