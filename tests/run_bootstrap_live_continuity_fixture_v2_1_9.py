from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from market_data_engine.models import Bar
from broker_integration_v1.bootstrap_live_continuity_validation_v2_1_9 import BootstrapLiveContinuityValidatorV219

def b(symbol,minute,close):
    t=datetime(2026,8,7,19,57,tzinfo=timezone.utc)+timedelta(minutes=minute)
    c=Decimal(str(close))
    return Bar(symbol,t,c,c+1,c-1,c,100+minute,10+minute,c)

class F:
    def fetch_recent_completed_bars(self,symbols,bars_per_symbol=3,lookback_days=7):
        return {s:[b(s,0,100),b(s,1,101),b(s,2,102)] for s in symbols}

v=BootstrapLiveContinuityValidatorV219(
    ["AAPL","MSFT","SPY"],
    bootstrap_client=F(),
)
base=v.bootstrap_only()
live=[
    b("AAPL",2,102.5),
    b("AAPL",3,103),
    b("MSFT",3,100),
    b("SPY",3,99),
]
r=v.validate_with_live_bars(base["bootstrap_bars"],live)

print("STATUS:",r["status"])
print("MERGED COUNTS:",r["merged_counts"])
print("DUPLICATE FREE:",r["duplicate_free"])
print("MONOTONIC:",r["monotonic"])
print("ELIGIBLE SIGNALS:",r["signal_result"]["decision_queue"]["eligible_signal_count"])
print("BROKER ORDERS:",r["broker_orders_submitted"])
print("PROD:",r["production_order_submission"])
print("LIVE:",r["live_trading"])
assert r["duplicate_free"] is True
assert r["monotonic"] is True
assert r["broker_orders_submitted"]==0
print("V2.1.9 SYNTHETIC CONTINUITY: PASS")
