$ErrorActionPreference = "Stop"
Set-Location C:\stock-bot

Write-Host "=== V1.7 HOLDOUT ZERO-TRADE ROOT-CAUSE + COVERAGE AUDIT ==="
python .\tools\audit_holdout_zero_trade_v1_7.py `
  --root C:\stock-bot `
  --start 2026-06-09 `
  --end 2026-07-07

if ($LASTEXITCODE -ne 0) { throw "V1.7 AUDIT FAILED" }

$out = ".\runtime\real_market_multitimeframe_shadow\latest_holdout_zero_trade_audit_v1_7.json"
if (-not (Test-Path $out)) { throw "OUTPUT MISSING: $out" }

Write-Host "RUN: PASS"
Write-Host "OUTPUT: $out"
