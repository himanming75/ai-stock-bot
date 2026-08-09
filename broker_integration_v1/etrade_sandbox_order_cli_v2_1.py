from __future__ import annotations

import argparse
import os
import webbrowser
from decimal import Decimal

from broker.contracts_v77_1 import BrokerOrderRequest, OrderSide, OrderType, TimeInForce
from .etrade_oauth_flow_v2 import ETradeOAuthFlow
from .etrade_sandbox_order_transport_v2_1 import ETradeSandboxOrderTransport
from .etrade_sandbox_order_pipeline_v2_1 import ETradeSandboxOrderPipeline


def _order_type(value):
    return {
        "market":OrderType.MARKET,
        "limit":OrderType.LIMIT,
        "stop":OrderType.STOP,
        "stop_limit":OrderType.STOP_LIMIT,
    }[value]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--account-id-key")
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

    print("E*TRADE SANDBOX ORDER V2.1")
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

    account=a.account_id_key or input("Sandbox accountIdKey: ").strip()
    symbol=(a.symbol or input("Symbol: ").strip()).upper()
    if not account or not symbol:
        raise RuntimeError("accountIdKey and symbol are required.")

    flow=ETradeOAuthFlow(key,secret,network_enabled=True,callback="oob")
    request=flow.request_token()
    rt=request.get("oauth_token")
    rs=request.get("oauth_token_secret")
    if not rt or not rs:
        raise RuntimeError("OAuth request token unavailable.")

    url=flow.authorization_url(rt)
    print("Authorization URL:",url)
    if not a.no_browser:
        try: webbrowser.open(url)
        except Exception: pass

    verifier=input("Paste E*TRADE verification code: ").strip()
    access=flow.access_token(rt,rs,verifier)
    at=access.get("oauth_token")
    aps=access.get("oauth_token_secret")
    if not at or not aps:
        raise RuntimeError("OAuth access token unavailable.")

    kwargs={}
    if a.limit_price is not None: kwargs["limit_price"]=Decimal(a.limit_price)
    if a.stop_price is not None: kwargs["stop_price"]=Decimal(a.stop_price)

    request_obj=BrokerOrderRequest(
        client_order_id="sandboxv21",
        symbol=symbol,
        side=OrderSide.BUY if a.side=="buy" else OrderSide.SELL,
        quantity=Decimal(a.quantity),
        order_type=_order_type(a.order_type),
        time_in_force=TimeInForce.DAY,
        strategy_id="ETRADE_SANDBOX_V2_1",
        **kwargs,
    )

    transport=ETradeSandboxOrderTransport(key,secret,at,aps,network_enabled=True)
    pipeline=ETradeSandboxOrderPipeline(transport)
    preview=pipeline.preview(account,request_obj,"SBX"+os.urandom(5).hex().upper())

    print("PREVIEW STATUS:",preview["status"])
    print("PREVIEW ID:",preview["preview_id"])
    print("Real money moved:",preview["real_money_moved"])

    if not a.place:
        print("PLACE: SKIPPED")
        print("Re-run with --place to test Sandbox Place Order.")
        return 0

    place=pipeline.place_from_preview(account,preview)
    print("PLACE STATUS:",place["status"])
    print("SANDBOX ORDER ID:",place["order_id"])
    print("Real money moved:",place["real_money_moved"])
    print("PROD order submission: LOCKED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
