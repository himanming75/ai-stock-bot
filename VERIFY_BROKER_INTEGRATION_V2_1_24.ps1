$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.paper_intraday_autonomous_session_status_v2_1_24 import build_v2_1_24_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_1_21_validator_reused'] is True; assert s['v2_1_22_paper_entry_reused'] is True; assert s['v2_1_23_lifecycle_reused'] is True; assert s['maximum_paper_orders_per_session']==1; assert s['automatic_exit_order_write'] is False; assert s['install_test_paper_orders']==0; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
