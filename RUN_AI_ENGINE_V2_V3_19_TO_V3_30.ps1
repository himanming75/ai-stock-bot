$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

Write-Host "========================================"
Write-Host " AI ENGINE V2 INTEGRATED BUILD"
Write-Host " V3.19 -> V3.30"
Write-Host "========================================"

& $Python .\dashboard\patch_ai_engine_v2_api.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_ai_engine_v2_ui.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m compileall -q .\ai_engine_v2
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile `
 .\dashboard\patch_ai_engine_v2_api.py `
 .\dashboard\patch_ai_engine_v2_ui.py `
 .\dashboard\verify_ai_engine_v2_utf8.py `
 .\dashboard\trade_analytics_v3_5.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== UNIT TESTS ==="
& $Python .\tests\test_ai_engine_v2_integrated_v3_19_to_v3_30.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== SYNTHETIC INTEGRATION TEST ==="
& $Python .\tests\run_ai_engine_v2_synthetic_fixture.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "RUN: PASS"
