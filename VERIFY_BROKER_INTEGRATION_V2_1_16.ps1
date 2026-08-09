$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.fresh_eligible_signal_evidence_capture_status_v2_1_16 import build_v2_1_16_status
s=build_v2_1_16_status()
print("STATUS:",s["status"])
print("V2.1.15 LEDGER REUSED:",s["v2_1_15_observation_ledger_reused"])
print("FRESH ONLY:",s["fresh_only_filter"])
print("ELIGIBLE ONLY:",s["eligible_only_filter"])
print("FINGERPRINT DEDUP:",s["fingerprint_deduplication"])
print("DEDICATED EVIDENCE LEDGER:",s["dedicated_evidence_ledger_ready"])
print("LATEST EVIDENCE:",s["latest_evidence_snapshot_ready"])
print("MARKET DATA FETCH:",s["market_data_fetch_from_stage"])
print("ETRADE OAUTH:",s["etrade_oauth_from_stage"])
print("SANDBOX PLACE:",s["sandbox_place_from_stage"])
print("BROKER ORDERS:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])

assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["v2_1_15_observation_ledger_reused"] is True
assert s["fresh_only_filter"] is True
assert s["eligible_only_filter"] is True
assert s["fingerprint_deduplication"] is True
assert s["market_data_fetch_from_stage"] is False
assert s["etrade_oauth_from_stage"] is False
assert s["sandbox_place_from_stage"] is False
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
assert s["contracts"]["duplicate_observer_loop_created"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
