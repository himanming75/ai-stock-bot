from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from market_data_engine.models import Bar
from broker_integration_v1.etrade_current_market_data_signal_bridge_v2_1_7 import CurrentMarketDataSignalBridgeV217

def b(symbol,i,close):
    t=datetime(2026,8,9,13,30,tzinfo=timezone.utc)+timedelta(minutes=i)
    c=Decimal(str(close))
    return Bar(symbol,t,c,c+1,c-1,c,100+i,10+i,c)

bars=[
 b("AAPL",0,100),b("AAPL",1,101),b("AAPL",2,103),
 b("SPY",0,100),b("SPY",1,99),b("SPY",2,97),
 b("MSFT",0,100),b("MSFT",1,100),b("MSFT",2,100),
]
r=CurrentMarketDataSignalBridgeV217().build_from_bars(bars)
for x in r["recommendations"]:
    print(x["symbol"],x["action"],x["confidence"])
print("ELIGIBLE:",r["decision_queue"]["eligible_signal_count"])
print("BROKER ORDERS:",r["broker_orders_submitted"])
print("NETWORK BY BRIDGE:",r["network_used_by_bridge"])
assert r["broker_orders_submitted"]==0
assert r["network_used_by_bridge"] is False
print("V2.1.7 CURRENT MARKET DATA SIGNAL BRIDGE: PASS")
