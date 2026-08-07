[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ throw "VENV PYTHON NOT FOUND: $Python" }

& $Python -m unittest `
  tools.test_shadow_counterfactual_v76_v80 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

$Text=Get-Content .\shadow_counterfactual_v76_v80\service.py -Raw
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
Write-Host "PARAMETER SCENARIOS: SHADOW ONLY"
Write-Host "ENTRY THRESHOLD: COUNTERFACTUAL ONLY"
Write-Host "EXIT/HOLD: COUNTERFACTUAL ONLY"
Write-Host "NOTIONAL/RISK: COUNTERFACTUAL ONLY"
Write-Host "ACTUAL PARAMETER CHANGES: OFF"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
