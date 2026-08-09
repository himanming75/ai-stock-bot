from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from market_data_engine.models import Bar
from broker_integration_v1.historical_bootstrap_live_continuation_v2_1_8 import HistoricalBootstrapLiveContinuationV218

def b(symbol,i,close):
    t=datetime(2026,8,7,13,30,tzinfo=timezone.utc)+timedelta(minutes=i)
    c=Decimal(str(close))
    return Bar(symbol,t,c,c+1,c-1,c,100+i,10+i,c)

class F:
    def fetch_recent_completed_bars(self,symbols,bars_per_symbol=3,lookback_days=7):
        return {s:[b(s,0,100),b(s,1,101),b(s,2,103)] for s in symbols}

r=HistoricalBootstrapLiveContinuationV218(
    ["AAPL","MSFT","SPY"],
    bootstrap_client=F(),
).bootstrap_signal()

print("STATUS:",r["status"])
print("BAR COUNTS:",r["bar_counts"])
print("BROKER ORDERS:",r["broker_orders_submitted"])
print("PROD:",r["production_order_submission"])
print("LIVE:",r["live_trading"])
assert r["broker_orders_submitted"]==0
assert r["production_order_submission"] is False
assert r["live_trading"] is False
print("V2.1.8 SYNTHETIC BOOTSTRAP: PASS")
