$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_threshold_calibration_challenger_policy_builder_v2_2_4.py
if($LASTEXITCODE -ne 0){throw "V2.2.4 TEST FAILED"}

& $Python -c "from ai_engine_v2.threshold_calibration_challenger_policy_builder_status_v2_2_4 import build_v2_2_4_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['confidence_grid_search']; assert s['reward_risk_grid_search']; assert s['regime_specific_candidates']; assert s['champion_policy_registry']; assert s['challenger_policy_registry']; assert not s['promotion_enabled']; assert not s['challenger_execution_enabled']; assert not s['execution_selector_modified']; assert s['paper_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.4 VERIFY FAILED"}
