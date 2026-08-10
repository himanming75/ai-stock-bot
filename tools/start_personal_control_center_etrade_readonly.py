from __future__ import annotations
import argparse
import os
import sys
import webbrowser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_oauth_flow_v2 import ETradeOAuthFlow
from web_controller.server import serve

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--host",default="127.0.0.1")
    p.add_argument("--port",type=int,default=8767)
    p.add_argument("--no-browser",action="store_true")
    a=p.parse_args()

    if a.host not in {"127.0.0.1","localhost"}:
        raise SystemExit("External binding is disabled.")

    key=os.environ.get("ETRADE_CONSUMER_KEY","").strip()
    secret=os.environ.get("ETRADE_CONSUMER_SECRET","").strip()
    if not key or not secret:
        print("STATUS: WAITING_FOR_ETRADE_CONSUMER_CREDENTIALS")
        print("Set ETRADE_CONSUMER_KEY and ETRADE_CONSUMER_SECRET in this PowerShell session.")
        return 3

    print("=== E*TRADE PRODUCTION READ-ONLY SESSION ===")
    print("OAuth token persistence: DISABLED")
    print("Production broker writes: LOCKED")
    print("Order submission: LOCKED")
    print("Live trading: LOCKED")

    flow=ETradeOAuthFlow(
        key,secret,
        network_enabled=True,
        callback="oob",
    )
    req=flow.request_token()
    rt=req.get("oauth_token")
    rs=req.get("oauth_token_secret")
    if not rt or not rs:
        raise RuntimeError("Request token response incomplete.")

    url=flow.authorization_url(rt)
    print("Authorization URL:",url)
    if not a.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    verifier=input("Paste E*TRADE verification code: ").strip()
    if not verifier:
        raise RuntimeError("Verification code is required.")

    access=flow.access_token(rt,rs,verifier)
    at=access.get("oauth_token")
    aps=access.get("oauth_token_secret")
    if not at or not aps:
        raise RuntimeError("Access token response incomplete.")

    # Tokens exist only in this process environment and its child calls.
    os.environ["ETRADE_ENVIRONMENT"]="PRODUCTION"
    os.environ["ETRADE_ALLOW_PRODUCTION_READ"]="YES"
    os.environ["ETRADE_ACCESS_TOKEN"]=at
    os.environ["ETRADE_ACCESS_SECRET"]=aps

    print("")
    print("STATUS: ETRADE_PRODUCTION_READONLY_SESSION_CONNECTED")
    print("Access token values: NOT DISPLAYED / NOT WRITTEN TO DISK")
    print(f"Starting Personal Control Center: http://{a.host}:{a.port}")
    print("Press Ctrl+C to stop and discard the in-memory session.")
    serve(ROOT,a.host,a.port)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
