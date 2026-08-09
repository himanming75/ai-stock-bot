from __future__ import annotations
import argparse
from .actual_intraday_canonical_e2e_validation_v2_1_21 import ActualIntradayCanonicalEndToEndValidatorV2121
def main():
    p=argparse.ArgumentParser(); p.add_argument("--root",default=r"C:\stock-bot"); p.add_argument("--symbols",default="AAPL,MSFT,SPY"); p.add_argument("--quantity",default="1"); a=p.parse_args()
    print("V2.1.21 ACTUAL INTRADAY CANONICAL END-TO-END VALIDATION")
    print("One cycle only. Outside regular window: no market-data runtime.")
    print("E*TRADE OAuth: DISABLED | Orders: DISABLED | PROD: LOCKED | LIVE: LOCKED")
    r=ActualIntradayCanonicalEndToEndValidatorV2121(a.root,[x.strip() for x in a.symbols.split(",")],a.quantity).run_once()
    print("\n=== V2.1.21 RESULT ===")
    for k in ("status","observed_at_utc","symbols","ready_for_manual_sandbox_review","automatic_sandbox_execution_allowed","broker_orders_submitted","production_order_submission","live_trading"):
        if k in r: print(k.upper()+":",r[k])
    return 0
if __name__=="__main__": raise SystemExit(main())
