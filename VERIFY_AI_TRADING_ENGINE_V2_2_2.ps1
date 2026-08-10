$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_outcome_labeling_feature_trade_binding_v2_2_2.py
if($LASTEXITCODE -ne 0){throw "V2.2.2 TEST FAILED"}

& $Python -c "from ai_engine_v2.outcome_labeling_feature_trade_binding_status_v2_2_2 import build_v2_2_2_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_1_feature_ledger_reused']; assert s['v2_1_27_completed_trade_ledger_reused']; assert s['actual_fill_outcomes_used_as_labels']; assert not s['pnl_recomputed']; assert s['max_feature_lag_seconds']==1800; assert not s['execution_selector_modified']; assert s['paper_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.2 VERIFY FAILED"}
