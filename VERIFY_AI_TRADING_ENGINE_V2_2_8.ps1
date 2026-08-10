$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_continuous_shadow_learning_pipeline_v2_2_8.py
if($LASTEXITCODE -ne 0){throw "V2.2.8 TEST FAILED"}

& $Python -c "from ai_engine_v2.continuous_shadow_learning_pipeline_status_v2_2_8 import build_v2_2_8_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_1_through_v2_2_7_orchestration']; assert s['canonical_shadow_change_detection']; assert s['actual_trade_ledger_change_detection']; assert s['continuous_supervisor']; assert s['fail_closed_stage_failure']; assert s['scorecard_foundation']; assert not s['promotion_enabled']; assert not s['automatic_policy_change_enabled']; assert not s['broker_network']; assert s['paper_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.8 VERIFY FAILED"}
