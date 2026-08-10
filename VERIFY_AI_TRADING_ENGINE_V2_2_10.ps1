$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_ml_model_training_validation_v2_2_10.py
if($LASTEXITCODE -ne 0){throw "V2.2.10 TEST FAILED"}

& $Python -c "from ai_engine_v2.ml_model_training_validation_status_v2_2_10 import build_v2_2_10_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['isolated_ml_venv']; assert s['validation_only_model_selection']; assert not s['test_used_for_selection']; assert s['test_evaluated_after_selection']; assert s['bounded_walk_forward']; assert s['walk_forward_embargo_market_dates']==1; assert not s['automatic_promotion']; assert not s['execution_selector_modified']; assert not s['broker_network']; assert s['orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.10 VERIFY FAILED"}
