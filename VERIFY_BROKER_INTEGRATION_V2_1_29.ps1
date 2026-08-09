$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.daily_risk_budget_kill_switch_status_v2_1_29 import build_v2_1_29_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_1_28_continuous_session_reused']; assert s['v2_1_27_completed_ledger_reused']; assert s['one_round_trip_per_delegated_call']; assert s['risk_rechecked_after_each_completed_round_trip']; assert s['daily_trade_cap']; assert s['daily_loss_budget']; assert s['consecutive_loss_guard']; assert s['manual_kill_switch']; assert s['install_test_paper_orders']==0; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
