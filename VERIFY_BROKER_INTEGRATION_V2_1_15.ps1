$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.freshness_guarded_persistent_observer_status_v2_1_15 import build_v2_1_15_status
s=build_v2_1_15_status()
print("STATUS:",s["status"])
print("V2.1.13 POLICY REUSED:",s["v2_1_13_observation_policy_reused"])
print("V2.1.14 SESSION GUARD REUSED:",s["v2_1_14_session_guard_reused"])
print("V2.1.14 FRESHNESS RUNTIME REUSED:",s["v2_1_14_freshness_runtime_reused"])
print("OUTSIDE WINDOW REST SKIP:",s["outside_window_rest_skip_ready"])
print("WAITING SESSION LEDGER:",s["waiting_session_ledger_ready"])
print("STALE BLOCK LEDGER:",s["stale_block_ledger_ready"])
print("FRESH OBSERVATION LEDGER:",s["fresh_observation_ledger_ready"])
print("ELIGIBLE ONLY WHEN FRESH:",s["eligible_capture_only_when_fresh"])
print("BOUNDED LOOP:",s["bounded_observation_loop"])
print("ETRADE OAUTH:",s["etrade_oauth_from_stage"])
print("SANDBOX PLACE:",s["sandbox_place_from_stage"])
print("BROKER ORDERS:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["outside_window_rest_skip_ready"] is True
assert s["eligible_capture_only_when_fresh"] is True
assert s["etrade_oauth_from_stage"] is False
assert s["sandbox_place_from_stage"] is False
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
assert s["contracts"]["duplicate_order_engine_created"] is False
print("VERIFY: PASS")
'@
$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
