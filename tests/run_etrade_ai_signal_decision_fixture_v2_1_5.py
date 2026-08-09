from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_ai_signal_bridge_v2_1_5 import ETradeAISignalDecisionBridge

payloads=[
    {"symbol":"AAPL","action":"BUY","confidence":"0.85","quantity":"1","strategy_id":"S1"},
    {"symbol":"MSFT","action":"HOLD","confidence":"0.95","quantity":"1","strategy_id":"S2"},
    {"symbol":"SPY","action":"SELL","confidence":"0.70","quantity":"1","strategy_id":"S3"},
    {"symbol":"QQQ","action":"BUY","confidence":"0.40","quantity":"1","strategy_id":"S4"},
]

result=ETradeAISignalDecisionBridge().build_signal_queue(payloads,max_signals=3)
print("ELIGIBLE SIGNALS:",result["eligible_signal_count"])
print("HOLD/BLOCK:",result["hold_or_block_count"])
for row in result["decisions"]:
    print(row["symbol"],row["strategy_action"],row["decision"],row["order_eligible"])

if result["eligible_signal_count"]!=2:
    raise SystemExit(2)
print("V2.1.5 SYNTHETIC SIGNAL DECISION: PASS")
