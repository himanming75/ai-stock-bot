$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_eligibility_block_reason_diagnostic_v2_1_31_3.py
if($LASTEXITCODE -ne 0){throw "V2.1.31.3 TEST FAILED"}

& $Python -c "from broker_integration_v1.eligibility_block_reason_diagnostic_status_v2_1_31_3 import build_v2_1_31_3_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['canonical_selector_reused']; assert s['v2_2_1_selector_explanation_reused']; assert s['symbol_level_block_reasons']; assert not s['execution_selector_modified']; assert not s['thresholds_modified']; assert not s['broker_network']; assert s['paper_orders']==0; assert s['live_orders']==0; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.1.31.3 VERIFY FAILED"}
