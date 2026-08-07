[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) { $Python = "python" }

& $Python -m unittest `
  tools.test_shadow_validation_v11_v15 `
  -v

if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "V11-V15 SHADOW VALIDATION: PASS"
Write-Host "BROKER WRITE: 0"
Write-Host "LIVE SUBMISSION: OFF"
Write-Host "ETRADE LIVE WRITE: OFF"
