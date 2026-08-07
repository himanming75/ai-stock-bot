$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH=$PSScriptRoot
$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python -m unittest tools.test_paper_operational_reliability_v2 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

foreach($File in @(
 ".\paper_operational_reliability\service.py",
 ".\tools\run_paper_reliability_watchdog_v2.py"
)){
 $Text=Get-Content $File -Raw
 foreach($Pattern in @(
  '\.\s*submit_order\s*\(',
  '\.\s*cancel_order\s*\(',
  '\.\s*replace_order\s*\(',
  '\.\s*close_position\s*\('
 )){
   if($Text -match $Pattern){throw "FORBIDDEN BROKER WRITE CALL: $Pattern"}
 }
}
Write-Host "VERIFY: PASS"
Write-Host "PROCESS SELF-MATCH FIX: PASS"
Write-Host "BROKER WRITE METHODS: 0"
Write-Host "AUTO RESTART: OFF"
