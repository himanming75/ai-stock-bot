$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.evidence_qualification_sandbox_readiness_gate_status_v2_1_17 import build_v2_1_17_status
s=build_v2_1_17_status()
print("STATUS:",s["status"])
print("V2.1.16 EVIDENCE REUSED:",s["v2_1_16_evidence_ledger_reused"])
print("CANONICAL CONFIDENCE FLOOR:",s["canonical_confidence_floor"])
print("FRESHNESS REQUIRED:",s["freshness_evidence_required"])
print("CANONICAL ALIGNMENT REQUIRED:",s["canonical_alignment_required"])
print("BUY/SELL ONLY:",s["buy_sell_only"])
print("POSITIVE QUANTITY:",s["positive_quantity_required"])
print("MAX SIGNALS:",s["max_signals_per_evidence"])
print("MANUAL REVIEW ONLY:",s["manual_sandbox_review_only"])
print("AUTO SANDBOX EXECUTION:",s["automatic_sandbox_execution_allowed"])
print("ETRADE OAUTH:",s["etrade_oauth_from_stage"])
print("SANDBOX PLACE:",s["sandbox_place_from_stage"])
print("BROKER ORDERS:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])

assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["canonical_confidence_floor"]=="0.60"
assert s["freshness_evidence_required"] is True
assert s["canonical_alignment_required"] is True
assert s["buy_sell_only"] is True
assert s["positive_quantity_required"] is True
assert s["max_signals_per_evidence"]==3
assert s["manual_sandbox_review_only"] is True
assert s["automatic_sandbox_execution_allowed"] is False
assert s["etrade_oauth_from_stage"] is False
assert s["sandbox_place_from_stage"] is False
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
assert s["contracts"]["duplicate_execution_controller_created"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
