$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.one_click_daily_paper_operation_status_v2_1_31 import build_v2_1_31_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_1_30_operational_entry_reused']; assert s['v2_1_29_daily_risk_reused']; assert s['market_open_wait_read_only']; assert s['startup_recovery_before_wait']; assert s['pre_risk_check_before_wait']; assert s['new_trading_state_machine_created'] is False; assert s['install_test_paper_orders']==0; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
