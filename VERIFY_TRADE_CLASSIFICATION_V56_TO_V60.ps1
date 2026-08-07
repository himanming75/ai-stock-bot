[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ throw "VENV PYTHON NOT FOUND: $Python" }

& $Python -m unittest `
  tools.test_trade_classification_v56_v60 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

$Text=Get-Content .\trade_classification_v56_v60\service.py -Raw
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
Write-Host "TRADE CLASSIFICATION: READ ONLY"
Write-Host "HOLDING PERIOD ANALYSIS: READ ONLY"
Write-Host "STRATEGY ATTRIBUTION: READ ONLY"
Write-Host "TRADE TAGGING: READ ONLY"
Write-Host "PERFORMANCE ATTRIBUTION: READ ONLY"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
