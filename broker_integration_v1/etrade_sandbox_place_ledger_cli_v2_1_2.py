from __future__ import annotations

import argparse
import json
import os
import webbrowser
from decimal import Decimal
from pathlib import Path

from broker.contracts_v77_1 import (
    BrokerOrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from .etrade_oauth_flow_v2 import ETradeOAuthFlow
from .etrade_network_transport_v2 import ETradeOAuthReadOnlyTransport
from .etrade_sandbox_order_transport_v2_1 import (
    ETradeSandboxOrderTransport,
    ETradeSandboxHTTPError,
)
from .etrade_sandbox_order_pipeline_v2_1 import ETradeSandboxOrderPipeline
from .etrade_sandbox_order_cli_v2_1 import _accounts, _select_account, _order_type
from .etrade_sandbox_order_ledger_v2_1_2 import SandboxOrderLedger
from .etrade_sandbox_orders_reader_v2_1_2 import ETradeSandboxOrdersReader
from .etrade_sandbox_order_reconciliation_v2_1_2 import reconcile_sandbox_place


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--symbol")
    p.add_argument("--quantity",default="1")
    p.add_argument("--side",choices=["buy","sell"],default="buy")
    p.add_argument(
        "--order-type",
        choices=["market","limit","stop","stop_limit"],
        default="market",
    )
    p.add_argument("--limit-price")
    p.add_argument("--stop-price")
    p.add_argument("--network",action="store_true")
    p.add_argument("--no-browser",action="store_true")
    a=p.parse_args()

    print("E*TRADE SANDBOX PLACE + LEDGER + RECONCILIATION V2.1.2")
    print("Environment: SANDBOX ONLY")
    print("PROD orders: LOCKED")
    print("Real money/securities: NONE")
    print("Profitability validation: NO")

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

    flow=ETradeOAuthFlow(
        key,
        secret,
        network_enabled=True,
        callback="oob",
    )
    request=flow.request_token()
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
    access=flow.access_token(
        request_token,
        request_secret,
        verifier,
    )
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

    kwargs={}
    if a.limit_price is not None:
        kwargs["limit_price"]=Decimal(a.limit_price)
    if a.stop_price is not None:
        kwargs["stop_price"]=Decimal(a.stop_price)

    order_request=BrokerOrderRequest(
        client_order_id="sandboxv212",
        symbol=symbol,
        side=OrderSide.BUY if a.side=="buy" else OrderSide.SELL,
        quantity=Decimal(a.quantity),
        order_type=_order_type(a.order_type),
        time_in_force=TimeInForce.DAY,
        strategy_id="ETRADE_SANDBOX_V2_1_2",
        **kwargs,
    )

    order_transport=ETradeSandboxOrderTransport(
        key,
        secret,
        access_token,
        access_secret,
        network_enabled=True,
    )
    pipeline=ETradeSandboxOrderPipeline(order_transport)
    ledger=SandboxOrderLedger(a.root)

    try:
        preview=pipeline.preview(
            account_id_key,
            order_request,
            "SBX"+os.urandom(5).hex().upper(),
        )
    except ETradeSandboxHTTPError as exc:
        print("PREVIEW FAILED:",exc.status)
        print(exc.response_body)
        return 10

    ledger.record_preview(
        account_id_key,
        order_request,
        preview,
    )

    print("")
    print("PREVIEW STATUS:",preview["status"])
    print("PREVIEW ID:",preview["preview_id"])
    print("Symbol:",symbol)
    print("Side:",a.side.upper())
    print("Quantity:",a.quantity)
    print("Real money moved: False")

    print("")
    confirmation=input(
        "Type PLACE to send this order to E*TRADE SANDBOX only / "
        "샌드박스 Place 실행 시 PLACE 입력: "
    ).strip()

    if confirmation!="PLACE":
        print("PLACE: CANCELED BY USER")
        print("Ledger: preview recorded")
        return 0

    try:
        place=pipeline.place_from_preview(
            account_id_key,
            preview,
        )
    except ETradeSandboxHTTPError as exc:
        print("PLACE FAILED:",exc.status)
        print(exc.response_body)
        return 11

    ledger.record_place(
        account_id_key,
        order_request,
        place,
    )

    print("")
    print("PLACE STATUS:",place["status"])
    print("SANDBOX ORDER ID:",place["order_id"])
    print("Real money moved: False")

    readonly=ETradeOAuthReadOnlyTransport(
        key,
        secret,
        access_token,
        access_secret,
        "https://apisb.etrade.com/v1",
        network_enabled=True,
    )
    reader=ETradeSandboxOrdersReader(readonly)
    read_result=reader.list_orders_safe(account_id_key)
    reconciliation=reconcile_sandbox_place(
        place,
        read_result["payload"],
    )
    if read_result["status"]!="PASS":
        reconciliation["orders_read_status"]=read_result["status"]
        reconciliation["orders_read_error"]=read_result["error"]

    ledger.record_reconciliation(
        account_id_key,
        reconciliation,
    )

    print("")
    print("RECONCILIATION STATUS:",reconciliation["status"])
    print("OBSERVED ORDERS:",reconciliation["observed_order_count"])
    print("MATCHED ORDERS:",reconciliation["matched_order_count"])
    print(
        "SANDBOX SAMPLE DATA POSSIBLE:",
        reconciliation["sandbox_sample_data_possible"],
    )
    print("Ledger:",ledger.path)
    print("PROD orders: LOCKED")
    print("Profitability validation: NO")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
