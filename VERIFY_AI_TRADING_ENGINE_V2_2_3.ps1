$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_performance_segmentation_feature_attribution_v2_2_3.py
if($LASTEXITCODE -ne 0){throw "V2.2.3 TEST FAILED"}

& $Python -c "from ai_engine_v2.performance_segmentation_feature_attribution_status_v2_2_3 import build_v2_2_3_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_2_labeled_outcomes_reused']; assert s['market_regime_segmentation']; assert s['confidence_segmentation']; assert s['reward_risk_segmentation']; assert s['alignment_segmentation']; assert s['quality_score_segmentation']; assert s['profit_factor']; assert s['minimum_actionable_sample']==5; assert not s['threshold_change_enabled']; assert not s['execution_selector_modified']; assert s['paper_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.3 VERIFY FAILED"}
