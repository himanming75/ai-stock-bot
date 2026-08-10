$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_ml_research_readiness_v2_2_13.py
if($LASTEXITCODE -ne 0){throw "V2.2.13 TEST FAILED"}

& $Python -c "from ai_engine_v2.ml_research_readiness_status_v2_2_13 import build_v2_2_13_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_12_outcomes_reused']; assert s['minimum_total_sample_gate']; assert s['minimum_per_horizon_gate']; assert s['edge_ready_sample_gate']; assert s['actual_class_coverage_gate']; assert s['research_readiness_only']; assert not s['selector_change_allowed']; assert not s['threshold_change_allowed']; assert not s['model_promotion_allowed']; assert not s['paper_execution_change_allowed']; assert not s['broker_network']; assert s['orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.13 VERIFY FAILED"}
