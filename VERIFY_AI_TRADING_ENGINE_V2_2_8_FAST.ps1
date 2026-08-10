$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"
& $Python .\tests\test_fast_data_acceleration_v2_2_8.py
if($LASTEXITCODE -ne 0){throw "V2.2.8 FAST TEST FAILED"}
& $Python -c "from ai_engine_v2.fast_data_acceleration_status_v2_2_8 import build_v2_2_8_fast_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['historical_multi_symbol_backfill']; assert s['configured_symbol_count']==30; assert s['forward_horizons']==[5,15,30,60]; assert s['mfe_mae_labels']; assert s['derived_ml_features']; assert s['live_30_symbol_shadow_collector']; assert not s['broker_trading_api_used']; assert s['paper_orders']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.2.8 FAST VERIFY FAILED"}
