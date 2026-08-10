$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"
& $Python .\tests\test_signal_scoring_feature_snapshot_v2_2_1.py
if($LASTEXITCODE -ne 0){throw "V2.2.1 TEST FAILED"}
& $Python -c "from ai_engine_v2.signal_scoring_feature_snapshot_status_v2_2_1 import build_v2_2_1_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['existing_canonical_engine_reused']; assert s['existing_canonical_selector_reused']; assert s['selector_block_reason_capture']; assert not s['quality_score_execution_enabled']; assert not s['execution_selector_modified']; assert s['paper_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.1 VERIFY FAILED"}
