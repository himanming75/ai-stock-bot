from __future__ import annotations

import argparse
import os
import webbrowser
from decimal import Decimal

from .canonically_aligned_end_to_end_runtime_v2_1_12 import (
    CanonicallyAlignedEndToEndRuntimeV2112,
)
from .etrade_oauth_flow_v2 import (
    ETradeOAuthFlow,
    ETradeOAuthHTTPError,
)
from .etrade_network_transport_v2 import (
    ETradeOAuthReadOnlyTransport,
)
from .etrade_sandbox_order_transport_v2_1 import (
    ETradeSandboxOrderTransport,
    ETradeSandboxHTTPError,
)
from .etrade_sandbox_order_cli_v2_1 import (
    _accounts,
    _select_account,
)
from .etrade_sandbox_autonomous_cycle_v2_1_3 import (
    ETradeSandboxAutonomousCycle,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument(
        "--symbols",
        nargs="+",
        default=["AAPL","MSFT","SPY"],
    )
    p.add_argument("--bootstrap-bars",type=int,default=3)
    p.add_argument("--quantity",default="1")
    p.add_argument("--cooldown-seconds",type=int,default=30)
    p.add_argument("--no-browser",action="store_true")
    a=p.parse_args()

    print("V2.1.12 CANONICALLY ALIGNED END-TO-END SANDBOX RUNTIME")
    print("Market data: ALPACA READ-ONLY")
    print("Canonical gate: REQUIRED")
    print("Execution target: E*TRADE SANDBOX ONLY")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")

    runtime=CanonicallyAlignedEndToEndRuntimeV2112(
        a.symbols,
        bootstrap_bars_per_symbol=a.bootstrap_bars,
    )

    plan=runtime.build_runtime_plan(
        quantity=Decimal(a.quantity)
    )

    print("")
    print("=== END-TO-END PLAN ===")
    print("STATUS:",plan["status"])
    print("BOOTSTRAP STATUS:",plan["bootstrap_status"])
    print("BOOTSTRAP COUNTS:",plan["bootstrap_counts"])
    print(
        "CANONICAL GATE ALIGNED:",
        plan["canonical_gate_aligned"],
    )
    print(
        "SIGNAL MIN CONFIDENCE:",
        plan["canonical_gate_alignment"]["signal_gate"][
            "minimum_confidence"
        ],
    )
    print(
        "PROMOTION MIN COMPARISONS:",
        plan["canonical_gate_alignment"]["promotion_gate"][
            "minimum_comparisons"
        ],
    )
    print(
        "MANUAL REVIEW REQUIRED:",
        plan["canonical_gate_alignment"]["promotion_gate"][
            "manual_review_required"
        ],
    )
    print("ELIGIBLE SIGNALS:",plan["eligible_signal_count"])

    for i,sig in enumerate(plan["eligible_signals"],1):
        print(
            i,
            sig.symbol,
            sig.side,
            "x"+str(sig.quantity),
            sig.strategy_id,
        )

    if plan["hold_only"]:
        print("")
        print("STATUS: PASS_END_TO_END_NO_ELIGIBLE_SIGNAL_NO_ORDER")
        print("E*TRADE OAuth: SKIPPED")
        print("Sandbox Preview/Place: SKIPPED")
        print("Broker Orders: 0")
        print("PROD: LOCKED")
        print("Live Trading: LOCKED")
        return 0

    confirm=input(
        "Type RUN_CANONICAL_SANDBOX to execute eligible signals in E*TRADE SANDBOX only: "
    ).strip()

    if confirm!="RUN_CANONICAL_SANDBOX":
        print("SANDBOX EXECUTION: CANCELED")
        return 0

    key=os.environ.get("ETRADE_CONSUMER_KEY")
    secret=os.environ.get("ETRADE_CONSUMER_SECRET")

    if not key or not secret:
        print("STATUS: WAITING_FOR_ETRADE_CREDENTIALS")
        return 3

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
    url=flow.authorization_url(rt)

    print("Authorization URL:",url)
    if not a.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    verifier=input(
        "Paste E*TRADE verification code: "
    ).strip()

    try:
        access=flow.access_token(rt,rs,verifier)
    except ETradeOAuthHTTPError as exc:
        print("OAUTH ACCESS TOKEN FAILED:",exc.status)
        print("RESPONSE BODY:",exc.response_body)
        return 11

    at=access.get("oauth_token")
    aps=access.get("oauth_token_secret")

    rows=_accounts(key,secret,at,aps)
    account_id_key,account_row=_select_account(rows)

    print(
        "SELECTED ACCOUNT:",
        account_row.get("accountDesc"),
    )

    order_transport=ETradeSandboxOrderTransport(
        key,
        secret,
        at,
        aps,
        network_enabled=True,
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

    try:
        result=runtime.execute_sandbox(
            plan=plan,
            account_id_key=account_id_key,
            cycle_engine=cycle_engine,
            root=a.root,
            cooldown_seconds=a.cooldown_seconds,
        )
    except ETradeSandboxHTTPError as exc:
        print("SANDBOX ORDER HTTP FAILED:",exc.status)
        print("RESPONSE BODY:",exc.response_body)
        return 20

    print("")
    print("=== V2.1.12 RESULT ===")
    print("STATUS:",result["status"])
    print(
        "CANONICAL GATE ALIGNED:",
        result["canonical_gate_aligned"],
    )
    print(
        "ELIGIBLE SIGNALS:",
        result["eligible_signal_count"],
    )
    print(
        "SUBMITTED CYCLES:",
        result["submitted_cycle_count"],
    )
    print(
        "SUCCESSFUL CYCLES:",
        result["successful_cycle_count"],
    )
    print(
        "STOPPED REASON:",
        result["stopped_reason"],
    )
    print(
        "REAL MONEY MOVED:",
        result["real_money_moved"],
    )
    print(
        "PROD ORDER SUBMISSION:",
        result["production_order_submission"],
    )
    print(
        "LIVE TRADING:",
        result["live_trading"],
    )
    return 0


if __name__=="__main__":
    raise SystemExit(main())
