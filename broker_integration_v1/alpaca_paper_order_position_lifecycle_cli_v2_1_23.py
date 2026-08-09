from __future__ import annotations
import argparse
from .alpaca_paper_order_position_lifecycle_bridge_v2_1_23 import AlpacaPaperOrderPositionLifecycleBridgeV2123

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--monitor",action="store_true")
    p.add_argument("--interval-seconds",type=int,default=5)
    p.add_argument("--max-cycles",type=int,default=12)
    a=p.parse_args()

    print("V2.1.23 ALPACA PAPER ORDER + POSITION LIFECYCLE")
    print("Existing Paper order lifecycle monitor: REUSED")
    print("Existing position exit rules: REUSED")
    print("Broker writes from this stage: DISABLED")
    print("Exit orders from this stage: DISABLED")
    print("Live trading: LOCKED")

    b=AlpacaPaperOrderPositionLifecycleBridgeV2123(a.root)
    r=(b.monitor_once(interval_seconds=a.interval_seconds,max_cycles=a.max_cycles)
       if a.monitor else b.build_dry_plan())

    print("\n=== V2.1.23 RESULT ===")
    for k in ("status","client_order_id","broker_order_id","position_lifecycle_state",
              "position_exit_decision","broker_read_performed","broker_write_performed",
              "exit_order_submitted","live_order_submitted"):
        if k in r: print(k.upper()+":",r[k])

    if not a.monitor:
        print("\nDRY PLAN ONLY. NO BROKER NETWORK.")
    return 0

if __name__=="__main__": raise SystemExit(main())
