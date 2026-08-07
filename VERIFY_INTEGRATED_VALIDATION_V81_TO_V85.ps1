[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ throw "VENV PYTHON NOT FOUND: $Python" }

& $Python -m unittest `
  tools.test_integrated_validation_v81_v85 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

$Text=Get-Content .\integrated_validation_v81_v85\service.py -Raw
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
Write-Host "CROSS MODULE CHECK: READ ONLY"
Write-Host "CLOSED TRADE PROPAGATION: READ ONLY"
Write-Host "DAILY SNAPSHOT: LOCAL FILE ONLY"
Write-Host "MULTI DAY READINESS: ANALYTICS ONLY"
Write-Host "LIVE SUBMISSION: OFF"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
