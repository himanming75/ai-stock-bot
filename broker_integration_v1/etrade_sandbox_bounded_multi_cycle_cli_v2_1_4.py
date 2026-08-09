from __future__ import annotations

import argparse
import os
import webbrowser
from decimal import Decimal

from .etrade_oauth_flow_v2 import ETradeOAuthFlow, ETradeOAuthHTTPError
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
from .etrade_sandbox_bounded_multi_cycle_v2_1_4 import (
    BoundedCyclePolicy,
    ETradeSandboxBoundedMultiCycleController,
)


def _read_signal(index):
    print("")
    print(f"=== SIGNAL {index} / 신호 {index} ===")
    symbol=input("Symbol (blank to stop adding signals): ").strip().upper()
    if not symbol:
        return None
    side=input("Side BUY/SELL [BUY]: ").strip().upper() or "BUY"
    if side not in {"BUY","SELL"}:
        raise ValueError("Side must be BUY or SELL.")
    quantity=input("Quantity [1]: ").strip() or "1"
    return SandboxCycleSignal(
        symbol=symbol,
        side=side,
        quantity=Decimal(quantity),
        order_type="MARKET",
        strategy_id="ETRADE_SANDBOX_V2_1_4",
    )


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--network",action="store_true")
    p.add_argument("--no-browser",action="store_true")
    p.add_argument("--max-cycles",type=int,default=3)
    p.add_argument("--cooldown-seconds",type=int,default=30)
    a=p.parse_args()

    policy=BoundedCyclePolicy(
        max_cycles=a.max_cycles,
        cooldown_seconds=a.cooldown_seconds,
        stop_on_error=True,
        duplicate_signal_guard=True,
    ).validate()

    print("E*TRADE SANDBOX BOUNDED MULTI-CYCLE V2.1.4")
    print("Environment: SANDBOX ONLY")
    print("Maximum cycles:",policy.max_cycles)
    print("Cooldown seconds:",policy.cooldown_seconds)
    print("Duplicate signal guard: ON")
    print("Kill switch: SUPPORTED")
    print("Unlimited loop: BLOCKED")
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

    signals=[]
    for i in range(1,policy.max_cycles+1):
        sig=_read_signal(i)
        if sig is None:
            break
        signals.append(sig)

    if not signals:
        print("NO SIGNALS PROVIDED")
        return 0

    flow=ETradeOAuthFlow(
        key,
        secret,
        network_enabled=True,
        callback="oob",
    )

    try:
        req=flow.request_token()
    except ETradeOAuthHTTPError as exc:
        print("OAUTH REQUEST TOKEN FAILED:",exc.status)
        print("RESPONSE BODY:",exc.response_body)
        return 10

    rt=req.get("oauth_token")
    rs=req.get("oauth_token_secret")
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

    try:
        access=flow.access_token(rt,rs,verifier)
    except ETradeOAuthHTTPError as exc:
        print("OAUTH ACCESS TOKEN FAILED:",exc.status)
        print("RESPONSE BODY:",exc.response_body)
        return 11

    at=access.get("oauth_token")
    aps=access.get("oauth_token_secret")
    if not at or not aps:
        raise RuntimeError("OAuth access token unavailable.")

    rows=_accounts(key,secret,at,aps)
    account_id_key,account_row=_select_account(rows)

    print("")
    print("SELECTED ACCOUNT:")
    print("Description:",account_row.get("accountDesc"))
    print("Mode:",account_row.get("accountMode"))
    print("Type:",account_row.get("accountType"))
    print("accountIdKey: not displayed")

    print("")
    print("=== BOUNDED PLAN / 제한 반복 계획 ===")
    for i,sig in enumerate(signals,1):
        print(
            f"{i}. {sig.symbol} {sig.side} x{sig.quantity} {sig.order_type}"
        )
    print("Maximum cycles:",policy.max_cycles)
    print("Cooldown seconds:",policy.cooldown_seconds)
    print("Duplicate guard: ON")
    print("Kill switch file:")
    print(
        rf"{a.root}\runtime\etrade_sandbox_multi_cycle_v2_1_4\KILL_SWITCH"
    )
    print("PROD orders: LOCKED")

    confirm=input(
        "Type RUN_BOUNDED to start bounded Sandbox cycles / "
        "제한 반복 실행 시 RUN_BOUNDED 입력: "
    ).strip()

    if confirm!="RUN_BOUNDED":
        print("BOUNDED MULTI-CYCLE: CANCELED")
        return 0

    order_transport=ETradeSandboxOrderTransport(
        key,secret,at,aps,network_enabled=True
    )
    readonly_transport=ETradeOAuthReadOnlyTransport(
        key,
        secret,
        at,
        aps,
        "https://apisb.etrade.com/v1",
        network_enabled=True,
    )
    cycle_engine=ETradeSandboxAutonomousCycle(
        order_transport,
        readonly_transport,
        a.root,
    )
    controller=ETradeSandboxBoundedMultiCycleController(
        cycle_engine,
        a.root,
        policy,
    )

    try:
        result=controller.run(account_id_key,signals)
    except ETradeSandboxHTTPError as exc:
        print("SANDBOX ORDER HTTP FAILED:",exc.status)
        print("RESPONSE BODY:",exc.response_body)
        return 20

    print("")
    print("=== BOUNDED MULTI-CYCLE RESULT ===")
    print("STATUS:",result["status"])
    print("SUBMITTED CYCLES:",result["submitted_cycle_count"])
    print("SUCCESSFUL CYCLES:",result["successful_cycle_count"])
    print("DUPLICATE BLOCKS:",result["duplicate_signal_block_count"])
    print("STOPPED REASON:",result["stopped_reason"])
    print("KILL SWITCH ACTIVE:",result["kill_switch_active"])
    print("REAL MONEY MOVED:",result["real_money_moved"])
    print("PROD ORDER SUBMISSION:",result["production_order_submission"])
    print("LIVE TRADING:",result["live_trading"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
