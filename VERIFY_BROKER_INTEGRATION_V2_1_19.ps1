$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.manual_approval_record_expiration_guard_status_v2_1_19 import build_v2_1_19_status

s=build_v2_1_19_status()
print("STATUS:",s["status"])
print("V2.1.18 PACKET REUSED:",s["v2_1_18_review_packet_reused"])
print("EXPLICIT PHRASE:",s["explicit_approval_phrase_required"])
print("PACKET FINGERPRINT:",s["packet_fingerprint_binding"])
print("DEFAULT EXPIRATION MINUTES:",s["default_approval_expiration_minutes"])
print("EXPIRATION GUARD:",s["approval_expiration_guard"])
print("DUPLICATE APPROVAL GUARD:",s["duplicate_approval_guard"])
print("ONE-TIME-USE STATE:",s["one_time_use_state_ready"])
print("APPROVAL CONSUMPTION:",s["approval_consumption_from_stage"])
print("MANUAL HANDOFF ONLY:",s["manual_handoff_only"])
print("AUTO SANDBOX EXECUTION:",s["automatic_sandbox_execution_allowed"])
print("ETRADE OAUTH:",s["etrade_oauth_from_stage"])
print("SANDBOX PLACE:",s["sandbox_place_from_stage"])
print("BROKER ORDERS:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])

assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["v2_1_18_review_packet_reused"] is True
assert s["explicit_approval_phrase_required"] is True
assert s["packet_fingerprint_binding"] is True
assert s["default_approval_expiration_minutes"]==15
assert s["approval_expiration_guard"] is True
assert s["duplicate_approval_guard"] is True
assert s["one_time_use_state_ready"] is True
assert s["approval_consumption_from_stage"] is False
assert s["manual_handoff_only"] is True
assert s["automatic_sandbox_execution_allowed"] is False
assert s["etrade_oauth_from_stage"] is False
assert s["sandbox_place_from_stage"] is False
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
