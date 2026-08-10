$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_champion_challenger_shadow_comparator_v2_2_5.py
if($LASTEXITCODE -ne 0){throw "V2.2.5 TEST FAILED"}

& $Python -c "from ai_engine_v2.champion_challenger_shadow_comparator_status_v2_2_5 import build_v2_2_5_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_1_feature_snapshot_reused']; assert s['v2_2_4_policy_registry_reused']; assert s['seed_fallback_when_registry_empty']; assert s['same_snapshot_comparison']; assert s['challenger_only_classification']; assert s['comparison_jsonl_ledger']; assert not s['challenger_execution_enabled']; assert not s['promotion_enabled']; assert not s['execution_selector_modified']; assert s['paper_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.5 VERIFY FAILED"}
