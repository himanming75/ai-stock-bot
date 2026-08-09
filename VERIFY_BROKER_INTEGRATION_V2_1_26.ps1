$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.full_alpaca_paper_round_trip_status_v2_1_26 import build_v2_1_26_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_1_21_validator_reused'] is True; assert s['v2_1_22_entry_reused'] is True; assert s['v2_1_23_lifecycle_reused'] is True; assert s['v2_1_25_exit_recovery_reused'] is True; assert s['recovery_first_state_machine'] is True; assert s['maximum_paper_entries_per_cycle']==1; assert s['maximum_paper_exits_per_cycle']==1; assert s['install_test_paper_orders']==0; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
