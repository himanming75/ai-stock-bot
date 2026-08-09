$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.session_crash_network_restart_recovery_status_v2_1_30 import build_v2_1_30_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_1_26_recovery_first_state_reused']; assert s['v2_1_27_final_reconciliation_reused']; assert s['v2_1_28_rollover_reused']; assert s['v2_1_29_daily_risk_and_kill_switch_reused']; assert s['bounded_network_read_retry']; assert s['local_vs_broker_state_reconciliation']; assert s['mismatch_fail_closed']; assert s['existing_kill_switch_reused_on_recovery_failure']; assert s['new_trading_state_machine_created'] is False; assert s['install_test_paper_orders']==0; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
