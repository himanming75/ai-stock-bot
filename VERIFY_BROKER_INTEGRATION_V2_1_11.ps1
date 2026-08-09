$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.canonical_gate_alignment_status_v2_1_11 import build_v2_1_11_status
from broker_integration_v1.canonical_gate_alignment_v2_1_11 import build_canonical_gate_alignment_v2_1_11

s=build_v2_1_11_status()
a=build_canonical_gate_alignment_v2_1_11()

print("STATUS:",s["status"])
print("CANONICAL SIGNAL MIN CONFIDENCE:",s["canonical_signal_min_confidence"])
print("CANONICAL PROMOTION MIN COMPARISONS:",s["canonical_promotion_min_comparisons"])
print("MANUAL PROMOTION ONLY:",s["manual_promotion_only"])
print("UNVERIFIED RR GATE ADDED:",s["unverified_rr_gate_added"])
print("UNVERIFIED CONFIDENCE OVERRIDE ADDED:",s["unverified_confidence_override_added"])
print("ALIGNMENT:",a["aligned"])
print("LIVE LOCKED:",a["safety_locks"]["live_trading_locked"])
print("BROKER WRITE LOCKED:",a["safety_locks"]["broker_write_locked"])
print("AUTO PROMOTION LOCKED:",a["safety_locks"]["automatic_promotion_locked"])
print("PROD POST:",a["production_order_post_allowed"])
print("LIVE:",a["live_trading_enabled"])

assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["canonical_signal_min_confidence"]=="0.60"
assert s["canonical_promotion_min_comparisons"]==20
assert s["unverified_rr_gate_added"] is False
assert s["unverified_confidence_override_added"] is False
assert a["aligned"] is True
assert a["production_order_post_allowed"] is False
assert a["live_trading_enabled"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
