$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.bootstrap_live_continuity_validation_status_v2_1_9 import build_v2_1_9_status
s=build_v2_1_9_status()
print("STATUS:",s["status"])
print("BOOTSTRAP V2.1.8 REUSED:",s["bootstrap_v2_1_8_reused"])
print("WS COLLECTOR V2.1.7.1 REUSED:",s["websocket_collector_v2_1_7_1_reused"])
print("TIMESTAMP DEDUP:",s["timestamp_deduplication"])
print("CHRONOLOGICAL MERGE:",s["chronological_merge"])
print("LIVE REPLACES SAME TS:",s["live_replaces_same_timestamp"])
print("SIGNAL RECALC:",s["signal_recalculation_after_merge"])
print("BROKER ORDER SUBMISSION:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
print("PROFIT VALIDATION:",s["profitability_validation"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["timestamp_deduplication"] is True
assert s["chronological_merge"] is True
assert s["live_replaces_same_timestamp"] is True
assert s["signal_recalculation_after_merge"] is True
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
assert s["contracts"]["duplicate_order_engine_created"] is False
print("VERIFY: PASS")
'@
$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
