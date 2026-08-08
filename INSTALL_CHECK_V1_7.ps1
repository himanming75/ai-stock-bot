$ErrorActionPreference = "Stop"
Set-Location C:\stock-bot

Write-Host "=== V1.7 INSTALL CHECK ==="
$required = @(
  ".\tools\build_real_market_multitimeframe_shadow.py",
  ".\paper_autonomous_execution\signals.py",
  ".\runtime\real_historical_ingestion\alpaca_real_historical_1min.jsonl",
  ".\tools\audit_holdout_zero_trade_v1_7.py",
  ".\tests\test_holdout_zero_trade_audit_v1_7.py"
)
foreach ($p in $required) {
  if (-not (Test-Path $p)) { throw "MISSING: $p" }
  Write-Host "OK $p"
}
python -m py_compile .\tools\audit_holdout_zero_trade_v1_7.py
if ($LASTEXITCODE -ne 0) { throw "PY_COMPILE FAILED" }
Write-Host "INSTALL CHECK: PASS"
