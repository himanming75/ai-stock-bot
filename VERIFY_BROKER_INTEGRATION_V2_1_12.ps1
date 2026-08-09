$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.canonically_aligned_end_to_end_runtime_status_v2_1_12 import build_v2_1_12_status

s=build_v2_1_12_status()

print("STATUS:",s["status"])
print("V2.1.8.2 BOOTSTRAP REUSED:",s["v2_1_8_2_bootstrap_reused"])
print("V2.1.9 SIGNAL PIPELINE REUSED:",s["v2_1_9_runtime_signal_pipeline_reused"])
print("V2.1.11 CANONICAL GATE REUSED:",s["v2_1_11_canonical_gate_reused"])
print("V2.1.10 ELIGIBLE BRIDGE REUSED:",s["v2_1_10_eligible_bridge_reused"])
print("V2.1.4 CONTROLLER REUSED:",s["v2_1_4_bounded_controller_reused"])
print("HOLD ZERO OAUTH/ORDER:",s["hold_zero_oauth_zero_order"])
print("EXPLICIT SANDBOX CONFIRM:",s["explicit_sandbox_confirmation_required_when_eligible"])
print("MAX SANDBOX CYCLES:",s["maximum_sandbox_cycles"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
print("PROFIT VALIDATION:",s["profitability_validation"])

assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["hold_zero_oauth_zero_order"] is True
assert s["explicit_sandbox_confirmation_required_when_eligible"] is True
assert s["maximum_sandbox_cycles"]==3
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
assert s["contracts"]["duplicate_order_engine_created"] is False
assert s["contracts"]["duplicate_signal_engine_created"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
