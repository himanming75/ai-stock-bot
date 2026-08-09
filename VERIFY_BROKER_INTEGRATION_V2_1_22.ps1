$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.alpaca_paper_bounded_execution_status_v2_1_22 import build_v2_1_22_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['existing_alpaca_paper_adapter_reused'] is True; assert s['new_broker_adapter_created'] is False; assert s['maximum_validation_notional']==25.0; assert s['maximum_bridge_submissions_per_session']==1; assert s['install_test_paper_orders']==0; assert s['live_order_submission_allowed'] is False; print('VERIFY: PASS')"
