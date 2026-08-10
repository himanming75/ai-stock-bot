$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_ml_shadow_inference_v2_2_11.py
if($LASTEXITCODE -ne 0){throw "V2.2.11 TEST FAILED"}

& $Python -c "from ai_engine_v2.ml_shadow_inference_status_v2_2_11 import build_v2_2_11_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_8_1_exact_feature_engineering_reused']; assert s['v2_2_10_selected_models_reused']; assert s['model_sha256_verified_before_load']; assert s['multi_horizon_inference']==[5,15,30,60]; assert s['research_ranking_only']; assert s['shadow_only']; assert not s['automatic_promotion']; assert not s['execution_selector_modified']; assert not s['broker_network']; assert s['paper_orders']==0; assert s['live_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.11 VERIFY FAILED"}
