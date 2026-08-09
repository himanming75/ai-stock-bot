$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.continuous_bounded_paper_session_status_v2_1_28 import build_v2_1_28_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['v2_1_26_round_trip_orchestrator_reused'] is True; assert s['v2_1_27_finalizer_reused'] is True; assert s['completed_ledger_proof_required_before_rollover'] is True; assert s['historical_ledgers_preserved'] is True; assert s['only_current_cycle_state_reset'] is True; assert s['new_entry_engine_created'] is False; assert s['new_exit_engine_created'] is False; assert s['default_max_completed_round_trips_per_session']==2; assert s['install_test_paper_orders']==0; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
