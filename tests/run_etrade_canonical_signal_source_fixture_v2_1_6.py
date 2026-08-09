from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from broker_integration_v1.etrade_canonical_signal_source_bridge_v2_1_6 import CanonicalSignalSourceBridgeV216

def row(symbol,macd,sig,roc,stoch):
    return {"symbol":symbol,"timeframe":"1Day","timestamp":"2026-08-08T00:00:00Z","source_close":100,
            "indicators":{"macd":macd,"macd_signal":sig,"roc":roc,"stochastic_k":stoch,
                          "bollinger_lower":90,"bollinger_upper":110}}

result=CanonicalSignalSourceBridgeV216().from_indicator_rows([
 row("AAPL",2,1,1,20),
 row("MSFT",1,1,0,50),
 row("SPY",1,2,-1,80),
])
for x in result["recommendations"]:
    print(x["symbol"],x["action"],x["confidence"])
print("ELIGIBLE:",result["decision_queue"]["eligible_signal_count"])
print("NETWORK:",result["network_requests_executed"])
print("BROKER ORDERS:",result["broker_orders_submitted"])
assert result["network_requests_executed"]==0
assert result["broker_orders_submitted"]==0
print("V2.1.6 CANONICAL SIGNAL SOURCE: PASS")
