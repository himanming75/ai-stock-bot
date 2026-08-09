$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.eligible_signal_to_sandbox_bridge_status_v2_1_10 import build_v2_1_10_status
s=build_v2_1_10_status()
print("STATUS:",s["status"])
print("V2.1.9 SUPPORTED:",s["v2_1_9_signal_result_supported"])
print("V2.1.5 QUEUE REUSED:",s["v2_1_5_eligible_queue_reused"])
print("V2.1.4 CONTROLLER REUSED:",s["v2_1_4_bounded_controller_reused"])
print("HOLD ZERO ORDER:",s["hold_zero_order_enforced"])
print("MAX SANDBOX CYCLES:",s["maximum_sandbox_cycles"])
print("DUPLICATE GUARD:",s["duplicate_guard_reused"])
print("KILL SWITCH:",s["kill_switch_reused"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["hold_zero_order_enforced"] is True
assert s["maximum_sandbox_cycles"]==3
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
assert s["contracts"]["duplicate_order_engine_created"] is False
assert s["contracts"]["duplicate_ledger_created"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
