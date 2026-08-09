from pathlib import Path
from datetime import datetime,timezone
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.market_session_freshness_guard_v2_1_14 import (
    build_session_freshness_gate,
)

now=datetime(2026,8,9,16,0,tzinfo=timezone.utc)
bars={
    "AAPL":datetime(2026,8,7,19,59,tzinfo=timezone.utc),
    "MSFT":datetime(2026,8,7,19,59,tzinfo=timezone.utc),
    "SPY":datetime(2026,8,7,20,0,tzinfo=timezone.utc),
}
r=build_session_freshness_gate(bars,now_utc=now)

print("STATUS:",r["status"])
print("REGULAR WINDOW:",r["session"]["inside_regular_clock_window"])
print("EXCHANGE OPEN CLAIMED:",r["session"]["exchange_open_claimed"])
print("ALL FRESH:",r["freshness"]["all_fresh"])
for symbol,row in r["freshness"]["per_symbol"].items():
    print(symbol,row["reason"],row["age_seconds"])
print("SIGNAL CAPTURE ALLOWED:",r["signal_capture_allowed"])
print("BROKER ORDERS:",r["broker_orders_submitted"])
print("PROD:",r["production_order_submission"])
print("LIVE:",r["live_trading"])
assert r["signal_capture_allowed"] is False
assert r["broker_orders_submitted"]==0
print("V2.1.14 SESSION/FRESHNESS GUARD: PASS")
