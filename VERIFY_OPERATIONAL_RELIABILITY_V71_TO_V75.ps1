[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ throw "VENV PYTHON NOT FOUND: $Python" }

& $Python -m unittest `
  tools.test_operational_reliability_v71_v75 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

$Text=Get-Content .\operational_reliability_v71_v75\service.py -Raw
$ForbiddenCalls=@(
 '\.\s*submit_order\s*\(',
 '\.\s*cancel_order\s*\(',
 '\.\s*replace_order\s*\(',
 '\.\s*close_position\s*\(',
 '\.\s*close_all_positions\s*\('
)

foreach($Pattern in $ForbiddenCalls){
 if($Text -match $Pattern){
   throw "FORBIDDEN BROKER WRITE CALL FOUND: $Pattern"
 }
}

Write-Host "VERIFY: PASS"
Write-Host "API RESILIENCE: READ ONLY"
Write-Host "LOCK RECOVERY: AUDIT ONLY"
Write-Host "LEDGER CONSISTENCY: READ ONLY"
Write-Host "RESOURCE MONITOR: READ ONLY"
Write-Host "AUTOMATIC REPAIR: OFF"
Write-Host "AUTOMATIC RECOVERY: OFF"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
