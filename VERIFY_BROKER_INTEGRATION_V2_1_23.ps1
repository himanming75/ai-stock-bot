$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.alpaca_paper_order_position_lifecycle_status_v2_1_23 import build_v2_1_23_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['existing_paper_order_lifecycle_monitor_reused'] is True; assert s['existing_position_exit_rules_reused'] is True; assert s['broker_write_allowed_from_stage'] is False; assert s['exit_order_submission_from_stage'] is False; assert s['install_test_paper_orders']==0; print('VERIFY: PASS')"
