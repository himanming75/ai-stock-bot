$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.historical_bootstrap_live_continuation_status_v2_1_8 import build_v2_1_8_status
s=build_v2_1_8_status()
print("STATUS:",s["status"])
print("HISTORICAL BOOTSTRAP:",s["historical_bootstrap_ready"])
print("LIVE CONTINUATION:",s["live_continuation_ready"])
print("REST READONLY:",s["alpaca_rest_readonly"])
print("V2.1.7 REUSED:",s["v2_1_7_signal_bridge_reused"])
print("BROKER ORDER SUBMISSION:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
print("PROFIT VALIDATION:",s["profitability_validation"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["historical_bootstrap_ready"] is True
assert s["live_continuation_ready"] is True
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
assert s["contracts"]["duplicate_indicator_engine_created"] is False
assert s["contracts"]["duplicate_signal_engine_created"] is False
print("VERIFY: PASS")
'@
$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
