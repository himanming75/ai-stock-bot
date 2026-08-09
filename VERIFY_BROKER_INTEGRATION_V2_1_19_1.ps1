$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.canonical_paper_gate_semantic_correction_status_v2_1_19_1 import build_v2_1_19_1_status
from broker_integration_v1.canonical_paper_gate_semantics_v2_1_19_1 import semantic_gate_contract_v2_1_19_1

s=build_v2_1_19_1_status()
c=semantic_gate_contract_v2_1_19_1()

print("STATUS:",s["status"])
print("GENERIC ETRADE CONFIDENCE:",s["generic_etrade_confidence"])
print("GENERIC IS CANONICAL PAPER:",s["generic_etrade_is_canonical_paper"])
print("CANONICAL PAPER CONFIDENCE:",s["canonical_paper_confidence"])
print("CANONICAL PAPER MIN RR:",s["canonical_paper_min_reward_risk"])
print("RR REQUIRED:",s["canonical_reward_risk_required"])
print("MISSING RR BLOCKS:",s["missing_reward_risk_blocks_readiness"])
print("V2.1.17 CORRECTED:",s["v2_1_17_qualification_corrected"])
print("LEGACY 0.60 LABEL REMOVED:",s["legacy_zero_point_60_canonical_label_removed"])
print("FALSE READY PREVENTED:",s["downstream_false_ready_prevented"])
print("AUTO SANDBOX EXECUTION:",s["automatic_sandbox_execution_allowed"])
print("ETRADE OAUTH:",s["etrade_oauth_from_stage"])
print("BROKER ORDERS:",s["broker_order_submission_from_stage"])
print("PROD:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])

assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["generic_etrade_confidence"]=="0.60"
assert s["generic_etrade_is_canonical_paper"] is False
assert s["canonical_paper_confidence"]=="0.75"
assert s["canonical_paper_min_reward_risk"]=="1.0"
assert s["canonical_reward_risk_required"] is True
assert s["missing_reward_risk_blocks_readiness"] is True
assert c["semantic_equivalence"] is False
assert s["automatic_sandbox_execution_allowed"] is False
assert s["etrade_oauth_from_stage"] is False
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
