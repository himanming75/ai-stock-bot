$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){
    ".\.venv\Scripts\python.exe"
}else{
    "python"
}

Write-Host "=== V3.4.1 RUNTIME IMPORT REPAIR ==="

& $Python .\dashboard\patch_v3_4_1_runtime_import.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile `
    .\dashboard\operations_dashboard_v3_2.py `
    .\dashboard\visualization_v3_4.py

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m unittest `
    .\tests\test_runtime_import_repair_v3_4_1.py

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
