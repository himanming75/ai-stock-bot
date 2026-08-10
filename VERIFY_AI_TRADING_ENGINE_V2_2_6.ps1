$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_champion_challenger_outcome_comparator_v2_2_6.py
if($LASTEXITCODE -ne 0){throw "V2.2.6 TEST FAILED"}

& $Python -c "from ai_engine_v2.champion_challenger_outcome_comparator_status_v2_2_6 import build_v2_2_6_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_2_actual_outcomes_reused']; assert s['v2_2_5_shadow_comparison_reused']; assert s['exact_snapshot_id_binding']; assert s['both_realized_metrics']; assert s['champion_only_realized_metrics']; assert s['challenger_only_shadow_coverage']; assert not s['counterfactual_pnl_fabricated']; assert not s['promotion_enabled']; assert not s['challenger_execution_enabled']; assert not s['execution_selector_modified']; assert s['paper_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.6 VERIFY FAILED"}
