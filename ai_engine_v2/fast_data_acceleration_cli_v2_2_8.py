from __future__ import annotations
import argparse
from pathlib import Path
from .fast_data_acceleration_v2_2_8 import (
    FastDataAccelerationV228,
    AlpacaMarketDataReadClientV228,
)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("status","backfill","label","live-once","live"),default="status")
    p.add_argument("--lookback-days",type=int,default=None)
    p.add_argument("--poll-seconds",type=int,default=None)
    p.add_argument("--max-runtime-seconds",type=int,default=None)
    a=p.parse_args()
    c=FastDataAccelerationV228(Path(a.root))

    if a.mode=="status":
        r=c.local_status()
    elif a.mode=="label":
        r=c.build_forward_labeled_dataset()
    else:
        client=AlpacaMarketDataReadClientV228()
        if a.mode=="backfill":
            r=c.historical_backfill(client,lookback_days=a.lookback_days)
        elif a.mode=="live-once":
            r=c.collect_live_once(client)
        else:
            r=c.collect_live_continuous(
                client,
                poll_seconds=a.poll_seconds,
                max_runtime_seconds=a.max_runtime_seconds,
            )

    print("=== V2.2.8 FAST DATA ACCELERATION ===")
    for k,v in r.items():
        if isinstance(v,(str,int,float,bool)) or v is None:
            print(f"{k.upper()}: {v}")
    return 0 if not str(r.get("status","")).startswith("BLOCKED_") else 2

if __name__=="__main__":
    raise SystemExit(main())
