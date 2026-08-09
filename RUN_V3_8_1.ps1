$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){
    ".\.venv\Scripts\python.exe"
}else{
    "python"
}

Write-Host "=== V3.8.1 CANONICAL PATCH REPAIR ==="

& $Python `
    .\dashboard\repair_canonical_lifecycle_patch_v3_8_1.py `
    --root C:\stock-bot

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "=== COMPILE ==="

& $Python -m py_compile `
    .\dashboard\trade_analytics_v3_5.py `
    .\dashboard\canonical_lifecycle_source_v3_8.py `
    .\dashboard\audit_lifecycle_source_v3_8.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "=== TEST ==="

& $Python -m unittest `
    .\tests\test_canonical_lifecycle_source_v3_8.py `
    .\tests\test_canonical_lifecycle_patch_repair_v3_8_1.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "=== AUDIT ==="

& $Python `
    .\dashboard\audit_lifecycle_source_v3_8.py `
    --root C:\stock-bot `
    --write

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "RUN: PASS"
