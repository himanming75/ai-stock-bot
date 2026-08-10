$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"
& $Python .\tests\test_ml_research_intelligence_bundle_v2_2_19_22.py
if($LASTEXITCODE -ne 0){throw "V2.2.19-22 TEST FAILED"}
& $Python -c "from ai_engine_v2.ml_research_intelligence_bundle_status_v2_2_19_22 import build_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['horizon_consensus']; assert s['uncertainty_scoring']; assert s['regime_segmentation']; assert s['research_recommendation_snapshot']; assert s['research_only']; assert not s['automatic_execution_change']; assert not s['automatic_selector_change']; assert not s['automatic_threshold_change']; assert not s['automatic_model_promotion']; assert not s['broker_network']; assert s['orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.19-22 VERIFY FAILED"}
