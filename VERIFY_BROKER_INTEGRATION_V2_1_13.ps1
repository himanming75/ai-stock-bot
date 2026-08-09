$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.persistent_market_observer_status_v2_1_13 import build_v2_1_13_status

s=build_v2_1_13_status()

print("STATUS:",s["status"])
print("V2.1.12 PLAN REUSED:",s["v2_1_12_end_to_end_plan_reused"])
print("CANONICAL GATE REUSED:",s["canonical_gate_reused"])
print("ELIGIBLE CAPTURE:",s["eligible_signal_capture_ready"])
print("JSONL LEDGER:",s["jsonl_observation_ledger_ready"])
print("BOUNDED LOOP:",s["bounded_observation_loop"])
print("UNCHANGED STOP:",s["unchanged_stop_guard"])
print("ETRADE OAUTH:",s["etrade_oauth_from_stage"])
print("SANDBOX PREVIEW:",s["sandbox_preview_from_stage"])
print("SANDBOX PLACE:",s["sandbox_place_from_stage"])
print("BROKER ORDER SUBMISSION:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])

assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["eligible_signal_capture_ready"] is True
assert s["jsonl_observation_ledger_ready"] is True
assert s["bounded_observation_loop"] is True
assert s["etrade_oauth_from_stage"] is False
assert s["sandbox_preview_from_stage"] is False
assert s["sandbox_place_from_stage"] is False
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
assert s["contracts"]["duplicate_order_engine_created"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
