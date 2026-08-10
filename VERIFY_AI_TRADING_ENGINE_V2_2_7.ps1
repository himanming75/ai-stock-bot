$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_challenger_shadow_execution_simulator_v2_2_7.py
if($LASTEXITCODE -ne 0){throw "V2.2.7 TEST FAILED"}

& $Python -c "from ai_engine_v2.challenger_shadow_execution_simulator_status_v2_2_7 import build_v2_2_7_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_2_1_feature_ledger_reused']; assert s['v2_2_5_challenger_only_signals_reused']; assert s['existing_position_exit_rule_reused']; assert s['canonical_1m_close_price_path']; assert s['counterfactual_shadow_execution']; assert not s['actual_broker_fill_used']; assert not s['broker_network']; assert s['paper_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.7 VERIFY FAILED"}
