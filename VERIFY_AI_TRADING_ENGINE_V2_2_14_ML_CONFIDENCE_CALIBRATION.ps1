$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_ml_confidence_calibration_v2_2_14.py
if($LASTEXITCODE -ne 0){throw "V2.2.14 TEST FAILED"}

& $Python -c "from ai_engine_v2.ml_confidence_calibration_status_v2_2_14 import build_v2_2_14_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_12_probability_outcomes_reused']; assert s['v2_2_13_readiness_gate_reused']; assert s['ten_bin_reliability']; assert s['expected_calibration_error']; assert s['multiclass_brier_score']; assert s['overconfidence_measure']; assert s['research_only']; assert not s['execution_use_allowed']; assert not s['selector_modified']; assert not s['threshold_modified']; assert not s['model_modified']; assert not s['model_promotion_allowed']; assert not s['broker_network']; assert s['orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.14 VERIFY FAILED"}
