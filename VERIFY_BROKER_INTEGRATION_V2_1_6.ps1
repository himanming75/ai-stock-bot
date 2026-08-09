$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.etrade_canonical_signal_source_status_v2_1_6 import build_etrade_canonical_signal_source_v2_1_6_status
s=build_etrade_canonical_signal_source_v2_1_6_status()
print("STATUS:",s["status"])
print("CANONICAL ENGINE:",s["canonical_signal_engine_reused"])
print("V2.1.5 REUSED:",s["v2_1_5_decision_bridge_reused"])
print("BUY/SELL/HOLD SOURCE:",s["buy_sell_hold_source_ready"])
print("MAX SIGNALS:",s["max_eligible_signals"])
print("NETWORK MARKET DATA:",s["network_market_data_enabled"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
print("PROFIT VALIDATION:",s["profitability_validation"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["canonical_signal_engine_reused"]=="V79.71-V79.75"
assert s["v2_1_5_decision_bridge_reused"] is True
assert s["network_market_data_enabled"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
assert s["contracts"]["duplicate_strategy_engine_created"] is False
print("VERIFY: PASS")
'@
$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
