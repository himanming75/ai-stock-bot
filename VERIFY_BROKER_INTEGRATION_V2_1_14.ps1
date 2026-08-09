$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.market_session_freshness_guard_status_v2_1_14 import build_v2_1_14_status
s=build_v2_1_14_status()
print("STATUS:",s["status"])
print("REGULAR WINDOW CLASSIFIER:",s["regular_window_classifier_ready"])
print("HOLIDAY OPEN CLAIM AVOIDED:",s["holiday_open_claim_avoided"])
print("BAR FRESHNESS GUARD:",s["bar_freshness_guard_ready"])
print("FUTURE TS GUARD:",s["future_timestamp_guard_ready"])
print("STALE SIGNAL BLOCK:",s["stale_signal_block_ready"])
print("V2.1.13 COMPATIBLE:",s["v2_1_13_observer_compatible"])
print("ETRADE OAUTH:",s["etrade_oauth_from_stage"])
print("SANDBOX PLACE:",s["sandbox_place_from_stage"])
print("BROKER ORDERS:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["holiday_open_claim_avoided"] is True
assert s["bar_freshness_guard_ready"] is True
assert s["stale_signal_block_ready"] is True
assert s["etrade_oauth_from_stage"] is False
assert s["sandbox_place_from_stage"] is False
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
print("VERIFY: PASS")
'@
$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
