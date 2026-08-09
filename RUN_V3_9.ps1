$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){
    ".\.venv\Scripts\python.exe"
}else{
    "python"
}

Write-Host "=== V3.9 CANONICAL PERFORMANCE + BILINGUAL DASHBOARD ==="

& $Python .\dashboard\patch_canonical_performance_v3_9.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_bilingual_dashboard_v3_9.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile `
    .\dashboard\operations_dashboard_v3_2.py `
    .\dashboard\trade_analytics_v3_5.py `
    .\dashboard\canonical_lifecycle_source_v3_8.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m unittest `
    .\tests\test_canonical_performance_bilingual_v3_9.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
