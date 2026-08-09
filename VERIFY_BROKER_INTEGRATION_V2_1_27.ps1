$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.final_exit_fill_reconciliation_round_trip_status_v2_1_27 import build_v2_1_27_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_1_23_entry_fill_reused'] is True; assert s['v2_1_25_exit_submission_reused'] is True; assert s['alpaca_paper_read_client_reused'] is True; assert s['completed_round_trip_dedup'] is True; assert s['fill_based_gross_pnl'] is True; assert s['fees_claimed_in_pnl'] is False; assert s['new_broker_write_created'] is False; assert s['install_test_paper_orders']==0; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
