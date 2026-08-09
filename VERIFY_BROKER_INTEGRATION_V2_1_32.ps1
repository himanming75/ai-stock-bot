$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.daily_performance_operation_report_status_v2_1_32 import build_v2_1_32_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_1_27_completed_round_trip_ledger_reused']; assert s['v2_1_29_risk_ledger_reused']; assert s['v2_1_30_recovery_ledger_reused']; assert s['v2_1_31_operation_ledger_reused']; assert s['pnl_recomputed_from_prices'] is False; assert s['v2_1_27_fill_based_pnl_aggregated']; assert s['json_daily_report']; assert s['markdown_daily_report']; assert s['validation_day_ledger']; assert s['new_execution_logic_created'] is False; assert s['broker_network_used'] is False; assert s['install_test_paper_orders']==0; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
