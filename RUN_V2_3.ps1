$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "=== V2.3 1D REGIME CONFLICT OUTCOME VALIDATION ==="
& $Python .\tools\audit_1d_regime_conflict_outcome_v2_3.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
