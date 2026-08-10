$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_ml_prediction_outcome_v2_2_12.py
if($LASTEXITCODE -ne 0){throw "V2.2.12 TEST FAILED"}

& $Python -c "from ai_engine_v2.ml_prediction_outcome_status_v2_2_12 import build_v2_2_12_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_11_inference_ledger_reused']; assert s['v2_2_8_1_market_bars_reused']; assert s['forward_horizons']==[5,15,30,60]; assert s['real_future_market_marks_only']; assert s['direction_accuracy_metrics']; assert s['edge_ready_segment_metrics']; assert s['deduplicated_outcome_ledger']; assert s['research_only']; assert not s['selector_change_recommendation_enabled']; assert not s['model_promotion_enabled']; assert not s['execution_selector_modified']; assert not s['broker_network']; assert s['paper_orders']==0; assert s['live_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.12 VERIFY FAILED"}
