from __future__ import annotations

import argparse
import json
import os
import webbrowser
from decimal import Decimal

from broker.contracts_v77_1 import BrokerOrderRequest, OrderSide, OrderType, TimeInForce
from .etrade_oauth_flow_v2 import ETradeOAuthFlow
from .etrade_network_transport_v2 import ETradeOAuthReadOnlyTransport
from .etrade_readonly_adapter import ETradeReadOnlyAdapter
from .etrade_sandbox_order_transport_v2_1 import (
    ETradeSandboxOrderTransport,
    ETradeSandboxHTTPError,
)
from .etrade_sandbox_order_pipeline_v2_1 import ETradeSandboxOrderPipeline


def _order_type(value):
    return {
        "market":OrderType.MARKET,
        "limit":OrderType.LIMIT,
        "stop":OrderType.STOP,
        "stop_limit":OrderType.STOP_LIMIT,
    }[value]


def _accounts(key,secret,token,token_secret):
    t=ETradeOAuthReadOnlyTransport(
        key,secret,token,token_secret,
        "https://apisb.etrade.com/v1",
        network_enabled=True,
    )
    a=ETradeReadOnlyAdapter(t)
    raw=a.list_accounts_raw()
    response=raw.get("AccountListResponse") or raw
    accounts=response.get("Accounts") or response.get("accounts") or {}
    rows=accounts.get("Account") or accounts.get("account") or []
    if isinstance(rows,dict):
        rows=[rows]
    return rows


def _select_account(rows):
    if not rows:
        raise RuntimeError("E*TRADE Sandbox returned no accounts.")
    print("")
    print("=== SANDBOX ACCOUNTS / 샌드박스 계좌 ===")
    for i,row in enumerate(rows,1):
        print(
            f"{i}. {row.get('accountDesc') or '-'} | "
            f"{row.get('accountMode') or '-'} | "
            f"{row.get('accountType') or '-'}"
        )
    while True:
        raw=input(f"Select account / 계좌 선택 [1-{len(rows)}]: ").strip()
        try:
            index=int(raw)-1
            if 0<=index<len(rows):
                chosen=rows[index]
                key=chosen.get("accountIdKey")
                if not key:
                    raise RuntimeError("Selected Sandbox account has no accountIdKey.")
                return key,chosen
        except ValueError:
            pass
        print("Invalid selection / 잘못된 선택입니다.")


def _safe_payload(payload):
    return payload


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol")
    p.add_argument("--quantity",default="1")
    p.add_argument("--side",choices=["buy","sell"],default="buy")
    p.add_argument("--order-type",choices=["market","limit","stop","stop_limit"],default="market")
    p.add_argument("--limit-price")
    p.add_argument("--stop-price")
    p.add_argument("--place",action="store_true")
    p.add_argument("--network",action="store_true")
    p.add_argument("--no-browser",action="store_true")
    a=p.parse_args()

    print("E*TRADE SANDBOX ORDER V2.1.1")
    print("Environment: SANDBOX ONLY")
    print("Network enabled:",bool(a.network))
    print("Place enabled:",bool(a.place))
    print("PROD order submission: LOCKED")
    print("Real money/securities: NONE")

    key=os.environ.get("ETRADE_CONSUMER_KEY")
    secret=os.environ.get("ETRADE_CONSUMER_SECRET")
    if not key or not secret:
        print("STATUS: WAITING_FOR_CREDENTIALS")
        return 3
    if not a.network:
        print("STATUS: READY_BUT_SANDBOX_NETWORK_NOT_ENABLED")
        return 4

    symbol=(a.symbol or input("Symbol: ").strip()).upper()
    if not symbol:
        raise RuntimeError("symbol is required.")

    flow=ETradeOAuthFlow(key,secret,network_enabled=True,callback="oob")
    request=flow.request_token()
    rt=request.get("oauth_token")
    rs=request.get("oauth_token_secret")
    if not rt or not rs:
        raise RuntimeError("OAuth request token unavailable.")

    url=flow.authorization_url(rt)
    print("Authorization URL:",url)
    if not a.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    verifier=input("Paste E*TRADE verification code: ").strip()
    access=flow.access_token(rt,rs,verifier)
    at=access.get("oauth_token")
    aps=access.get("oauth_token_secret")
    if not at or not aps:
        raise RuntimeError("OAuth access token unavailable.")

    rows=_accounts(key,secret,at,aps)
    account,account_row=_select_account(rows)

    print("")
    print("SELECTED ACCOUNT:")
    print("Description:",account_row.get("accountDesc"))
    print("Mode:",account_row.get("accountMode"))
    print("Type:",account_row.get("accountType"))
    print("accountIdKey: obtained directly from current OAuth session (not displayed)")

    kwargs={}
    if a.limit_price is not None:
        kwargs["limit_price"]=Decimal(a.limit_price)
    if a.stop_price is not None:
        kwargs["stop_price"]=Decimal(a.stop_price)

    request_obj=BrokerOrderRequest(
        client_order_id="sandboxv211",
        symbol=symbol,
        side=OrderSide.BUY if a.side=="buy" else OrderSide.SELL,
        quantity=Decimal(a.quantity),
        order_type=_order_type(a.order_type),
        time_in_force=TimeInForce.DAY,
        strategy_id="ETRADE_SANDBOX_V2_1_1",
        **kwargs,
    )

    transport=ETradeSandboxOrderTransport(key,secret,at,aps,network_enabled=True)
    pipeline=ETradeSandboxOrderPipeline(transport)

    print("")
    print("=== PREVIEW REQUEST DIAGNOSTIC ===")
    print("Symbol:",symbol)
    print("Side:",a.side.upper())
    print("Quantity:",a.quantity)
    print("Order type:",a.order_type.upper())
    print("Endpoint: current selected sandbox account /orders/preview.json")

    try:
        preview=pipeline.preview(account,request_obj,"SBX"+os.urandom(5).hex().upper())
    except ETradeSandboxHTTPError as exc:
        print("")
        print("=== E*TRADE PREVIEW REJECTED ===")
        print("HTTP STATUS:",exc.status)
        print("ETRADE RESPONSE BODY:")
        print(exc.response_body)
        print("")
        print("No Sandbox Place request was sent.")
        print("PROD order submission: LOCKED")
        return 10

    print("PREVIEW STATUS:",preview["status"])
    print("PREVIEW ID:",preview["preview_id"])
    print("Real money moved:",preview["real_money_moved"])

    if not a.place:
        print("PLACE: SKIPPED")
        print("Preview test complete.")
        return 0

    try:
        place=pipeline.place_from_preview(account,preview)
    except ETradeSandboxHTTPError as exc:
        print("")
        print("=== E*TRADE PLACE REJECTED ===")
        print("HTTP STATUS:",exc.status)
        print("ETRADE RESPONSE BODY:")
        print(exc.response_body)
        print("PROD order submission: LOCKED")
        return 11

    print("PLACE STATUS:",place["status"])
    print("SANDBOX ORDER ID:",place["order_id"])
    print("Real money moved:",place["real_money_moved"])
    print("PROD order submission: LOCKED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
