$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_ml_feature_drift_v2_2_15.py
if($LASTEXITCODE -ne 0){throw "V2.2.15 TEST FAILED"}

& $Python -c "from ai_engine_v2.ml_feature_drift_status_v2_2_15 import build_v2_2_15_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_9_training_features_reused']; assert s['v2_2_11_inference_features_reused']; assert s['mean_shift_monitoring']; assert s['median_iqr_shift_monitoring']; assert s['scale_ratio_monitoring']; assert s['feature_level_severity']; assert s['research_only']; assert not s['automatic_retraining_allowed']; assert not s['automatic_model_replacement_allowed']; assert not s['execution_change_allowed']; assert not s['selector_modified']; assert not s['threshold_modified']; assert not s['broker_network']; assert s['orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.15 VERIFY FAILED"}
