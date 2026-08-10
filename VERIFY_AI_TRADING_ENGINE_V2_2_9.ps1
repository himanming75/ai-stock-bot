$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_training_dataset_builder_v2_2_9.py
if($LASTEXITCODE -ne 0){throw "V2.2.9 TEST FAILED"}

& $Python -c "from ai_engine_v2.training_dataset_builder_status_v2_2_9 import build_v2_2_9_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['streaming_two_pass_builder']; assert s['chronological_market_date_split']; assert s['train_validation_test']; assert s['embargo_trading_days']==1; assert not s['random_shuffle_before_split']; assert s['future_target_leakage_guard']; assert s['horizons']==[5,15,30,60]; assert not s['broker_network']; assert s['orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.9 VERIFY FAILED"}
