$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"
& $Python .\tests\test_ml_model_health_bundle_v2_2_16_18.py
if($LASTEXITCODE -ne 0){throw "V2.2.16-18 TEST FAILED"}
& $Python -c "from ai_engine_v2.ml_model_health_bundle_status_v2_2_16_18 import build_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_13_readiness_reused']; assert s['v2_2_14_calibration_reused']; assert s['v2_2_15_feature_drift_reused']; assert s['model_health_gate']; assert s['retraining_trigger_planner']; assert s['candidate_evaluation_snapshot']; assert not s['automatic_retraining']; assert not s['automatic_promotion']; assert not s['execution_change']; assert not s['broker_network']; assert s['orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.16-18 VERIFY FAILED"}
