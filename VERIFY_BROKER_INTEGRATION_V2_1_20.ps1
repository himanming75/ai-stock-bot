$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.canonical_reward_risk_provenance_status_v2_1_20 import build_v2_1_20_status

s=build_v2_1_20_status()
print("STATUS:",s["status"])
print("BASE COMMIT:",s["base_commit"])
print("V2.1.16 EVIDENCE REUSED:",s["v2_1_16_evidence_reused"])
print("EXISTING CANONICAL ANALYSIS REUSED:",s["existing_canonical_analysis_reused"])
print("CANONICAL ENGINE:",s["canonical_engine"])
print("CANONICAL SELECTOR:",s["canonical_selector"])
print("CANONICAL CONFIDENCE:",s["canonical_min_confidence"])
print("CANONICAL MIN RR:",s["canonical_min_reward_risk"])
print("RR RECOMPUTED:",s["reward_risk_formula_recomputed"])
print("SYMBOL MATCH REQUIRED:",s["symbol_match_required"])
print("ACTION/SIDE MATCH REQUIRED:",s["action_side_match_required"])
print("SHA256 PROVENANCE:",s["sha256_provenance_binding"])
print("V2.1.17 SOURCE REDIRECT:",s["v2_1_17_source_redirected_to_v2_1_20"])
print("MARKET DATA FETCH:",s["market_data_fetch_from_stage"])
print("ETRADE OAUTH:",s["etrade_oauth_from_stage"])
print("SANDBOX PLACE:",s["sandbox_place_from_stage"])
print("BROKER ORDERS:",s["broker_order_submission_from_stage"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])

assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["canonical_min_confidence"]=="0.75"
assert s["canonical_min_reward_risk"]=="1.0"
assert s["reward_risk_formula_recomputed"] is False
assert s["symbol_match_required"] is True
assert s["action_side_match_required"] is True
assert s["sha256_provenance_binding"] is True
assert s["v2_1_17_source_redirected_to_v2_1_20"] is True
assert s["market_data_fetch_from_stage"] is False
assert s["etrade_oauth_from_stage"] is False
assert s["sandbox_place_from_stage"] is False
assert s["broker_order_submission_from_stage"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
