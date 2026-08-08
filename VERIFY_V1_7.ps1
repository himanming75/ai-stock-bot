$ErrorActionPreference = "Stop"
Set-Location C:\stock-bot

Write-Host "=== V1.7 TEST + VERIFY ==="
python -m unittest .\tests\test_holdout_zero_trade_audit_v1_7.py
if ($LASTEXITCODE -ne 0) { throw "UNIT TEST FAILED" }

$out = ".\runtime\real_market_multitimeframe_shadow\latest_holdout_zero_trade_audit_v1_7.json"
if (-not (Test-Path $out)) { throw "RUN V1.7 FIRST: output missing" }

$r = Get-Content $out -Raw | ConvertFrom-Json
if ($r.stage -ne "V1.7_HOLDOUT_ZERO_TRADE_ROOT_CAUSE_DATA_SIGNAL_COVERAGE_AUDIT") {
  throw "UNEXPECTED STAGE"
}
if ($r.status -ne "PASS") { throw "AUDIT STATUS NOT PASS" }
if ($r.contracts.paper_runtime_modified -ne $false) { throw "PAPER RUNTIME CONTRACT VIOLATION" }
if ($r.contracts.production_parameter_modified -ne $false) { throw "PRODUCTION PARAMETER CONTRACT VIOLATION" }
if ($r.contracts.broker_write_performed -ne $false) { throw "BROKER WRITE CONTRACT VIOLATION" }
if ($r.contracts.order_submission_performed -ne $false) { throw "ORDER SUBMISSION CONTRACT VIOLATION" }
if ($r.canonical_reuse.duplicate_engine_created -ne $false) { throw "DUPLICATE ENGINE CONTRACT VIOLATION" }

Write-Host ""
Write-Host "ZERO-TRADE DATES:" $r.scope_summary.zero_trade_dates
Write-Host "ROOT CAUSES:"
$r.scope_summary.zero_trade_day_root_cause_counts | ConvertTo-Json -Depth 5
Write-Host ""
Write-Host "INTERPRETATION:"
$r.interpretation | ConvertTo-Json -Depth 5
Write-Host ""
Write-Host "VERIFY: PASS"
