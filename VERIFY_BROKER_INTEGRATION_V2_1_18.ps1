$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.manual_sandbox_review_packet_builder_status_v2_1_18 import build_v2_1_18_status
s=build_v2_1_18_status()
print("STATUS:",s["status"])
print("V2.1.17 QUALIFICATION REUSED:",s["v2_1_17_qualification_ledger_reused"])
print("READY ONLY:",s["ready_only_packet_build"])
print("JSON PACKET:",s["json_packet_ready"])
print("MARKDOWN PACKET:",s["markdown_packet_ready"])
print("MANUAL CHECKLIST:",s["manual_checklist_ready"])
print("PACKET DEDUP:",s["packet_deduplication_ready"])
print("MANUAL REVIEW REQUIRED:",s["manual_review_required"])
print("MANUAL APPROVAL RECORDING:",s["manual_approval_recording_from_stage"])
print("AUTO SANDBOX EXECUTION:",s["automatic_sandbox_execution_allowed"])
print("ETRADE OAUTH:",s["etrade_oauth_from_stage"])
print("SANDBOX PLACE:",s["sandbox_place_from_stage"])
print("BROKER ORDERS:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["ready_only_packet_build"] is True
assert s["manual_review_required"] is True
assert s["manual_approval_recording_from_stage"] is False
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
