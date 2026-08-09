$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -c "from broker_integration_v1.actual_intraday_canonical_e2e_validation_status_v2_1_21 import build_v2_1_21_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['canonical_min_confidence']=='0.75'; assert s['canonical_min_reward_risk']=='1.0'; assert s['broker_order_submission_from_stage'] is False; assert s['live_trading_enabled'] is False; print('VERIFY: PASS')"
