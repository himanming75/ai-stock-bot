$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.alpaca_paper_exit_execution_recovery_status_v2_1_25 import build_v2_1_25_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_1_23_exit_ready_required'] is True; assert s['existing_paper_true_client_reused'] is True; assert s['alpaca_official_close_position_used'] is True; assert s['new_live_client_created'] is False; assert s['one_time_exit_fingerprint_guard'] is True; assert s['install_test_paper_exit_orders']==0; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
