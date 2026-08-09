$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){
    ".\.venv\Scripts\python.exe"
}else{
    "python"
}

Write-Host "=== V3.6 TRADE LEDGER NORMALIZATION ==="

& $Python .\dashboard\patch_trade_analytics_v3_6.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile `
    .\dashboard\trade_analytics_v3_5.py `
    .\dashboard\trade_ledger_normalizer_v3_6.py `
    .\dashboard\audit_trade_recovery_v3_6.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m unittest `
    .\tests\test_trade_ledger_normalization_v3_6.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== RECOVERY AUDIT ==="

& $Python .\dashboard\audit_trade_recovery_v3_6.py `
    --root C:\stock-bot `
    --write
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
