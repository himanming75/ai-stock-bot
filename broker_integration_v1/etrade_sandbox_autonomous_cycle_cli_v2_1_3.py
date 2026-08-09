from __future__ import annotations

import argparse
import os
import webbrowser
from decimal import Decimal

from .etrade_oauth_flow_v2 import (
    ETradeOAuthFlow,
    ETradeOAuthHTTPError,
)
from .etrade_network_transport_v2 import ETradeOAuthReadOnlyTransport
from .etrade_sandbox_order_transport_v2_1 import (
    ETradeSandboxOrderTransport,
    ETradeSandboxHTTPError,
)
from .etrade_sandbox_order_cli_v2_1 import _accounts, _select_account
from .etrade_sandbox_autonomous_cycle_v2_1_3 import (
    SandboxCycleSignal,
    ETradeSandboxAutonomousCycle,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--symbol")
    p.add_argument("--side",choices=["BUY","SELL"],default="BUY")
    p.add_argument("--quantity",default="1")
    p.add_argument("--network",action="store_true")
    p.add_argument("--no-browser",action="store_true")
    a=p.parse_args()

    print("E*TRADE SANDBOX AUTONOMOUS CYCLE V2.1.3")
    print("Mode: ONE CYCLE ONLY")
    print("Environment: SANDBOX ONLY")
    print("Automatic repeat: DISABLED")
    print("PROD orders: LOCKED")
    print("Real money/securities: NONE")

    key=os.environ.get("ETRADE_CONSUMER_KEY")
    secret=os.environ.get("ETRADE_CONSUMER_SECRET")
    if not key or not secret:
        print("STATUS: WAITING_FOR_CREDENTIALS")
        return 3
    if not a.network:
        print("STATUS: NETWORK_NOT_ENABLED")
        return 4

    symbol=(a.symbol or input("Symbol: ").strip()).upper()
    if not symbol:
        raise RuntimeError("Symbol is required.")

    flow=ETradeOAuthFlow(
        key,
        secret,
        network_enabled=True,
        callback="oob",
    )

    try:
        request=flow.request_token()
    except ETradeOAuthHTTPError as exc:
        print("OAUTH REQUEST TOKEN FAILED:",exc.status)
        print("RESPONSE BODY:",exc.response_body)
        return 10

    request_token=request.get("oauth_token")
    request_secret=request.get("oauth_token_secret")
    if not request_token or not request_secret:
        raise RuntimeError("OAuth request token unavailable.")

    url=flow.authorization_url(request_token)
    print("Authorization URL:",url)

    if not a.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    verifier=input("Paste E*TRADE verification code: ").strip()

    try:
        access=flow.access_token(
            request_token,
            request_secret,
            verifier,
        )
    except ETradeOAuthHTTPError as exc:
        print("OAUTH ACCESS TOKEN FAILED:",exc.status)
        print("RESPONSE BODY:",exc.response_body)
        return 11

    access_token=access.get("oauth_token")
    access_secret=access.get("oauth_token_secret")
    if not access_token or not access_secret:
        raise RuntimeError("OAuth access token unavailable.")

    rows=_accounts(
        key,
        secret,
        access_token,
        access_secret,
    )
    account_id_key,account_row=_select_account(rows)

    print("")
    print("SELECTED ACCOUNT:")
    print("Description:",account_row.get("accountDesc"))
    print("Mode:",account_row.get("accountMode"))
    print("Type:",account_row.get("accountType"))
    print("accountIdKey: not displayed")

    signal=SandboxCycleSignal(
        symbol=symbol,
        side=a.side,
        quantity=Decimal(a.quantity),
        order_type="MARKET",
    )

    print("")
    print("=== ONE-CYCLE PLAN / 1회 자동 사이클 계획 ===")
    print("Symbol:",signal.symbol)
    print("Side:",signal.side)
    print("Quantity:",signal.quantity)
    print("Order type:",signal.order_type)
    print("Flow: Preview -> Sandbox Place -> Ledger -> Reconciliation")
    print("Automatic repeat: DISABLED")
    print("PROD orders: LOCKED")

    confirm=input(
        "Type RUN_ONCE to execute one Sandbox autonomous cycle / "
        "1회 실행 시 RUN_ONCE 입력: "
    ).strip()

    if confirm!="RUN_ONCE":
        print("AUTONOMOUS CYCLE: CANCELED")
        return 0

    order_transport=ETradeSandboxOrderTransport(
        key,
        secret,
        access_token,
        access_secret,
        network_enabled=True,
    )

    readonly_transport=ETradeOAuthReadOnlyTransport(
        key,
        secret,
        access_token,
        access_secret,
        "https://apisb.etrade.com/v1",
        network_enabled=True,
    )

    cycle=ETradeSandboxAutonomousCycle(
        order_transport,
        readonly_transport,
        a.root,
    )

    try:
        result=cycle.run_once(
            account_id_key,
            signal,
            "AUTO"+os.urandom(5).hex().upper(),
        )
    except ETradeSandboxHTTPError as exc:
        print("SANDBOX ORDER HTTP FAILED:",exc.status)
        print("RESPONSE BODY:",exc.response_body)
        return 20

    print("")
    print("=== AUTONOMOUS CYCLE RESULT ===")
    print("STATUS:",result["status"])
    print("PREVIEW:",result["preview_status"])
    print("PLACE:",result["place_status"])
    print("SANDBOX ORDER ID:",result["sandbox_order_id"])
    print("RECONCILIATION:",result["reconciliation_status"])
    print("OBSERVED ORDERS:",result["observed_order_count"])
    print("MATCHED ORDERS:",result["matched_order_count"])
    print("LEDGER:",result["ledger_path"])
    print("REAL MONEY MOVED:",result["real_money_moved"])
    print("PROD ORDER SUBMISSION:",result["production_order_submission"])
    print("AUTOMATIC REPEAT: DISABLED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
