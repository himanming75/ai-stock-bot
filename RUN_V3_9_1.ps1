$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){
    ".\.venv\Scripts\python.exe"
}else{
    "python"
}

Write-Host "=== V3.9.1 BILINGUAL VERIFY ENCODING REPAIR ==="

& $Python -m py_compile `
    .\dashboard\verify_bilingual_utf8_v3_9_1.py `
    .\dashboard\operations_dashboard_v3_2.py `
    .\dashboard\trade_analytics_v3_5.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

& $Python -m unittest `
    .\tests\test_canonical_performance_bilingual_v3_9.py `
    .\tests\test_bilingual_verify_encoding_v3_9_1.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "RUN: PASS"
