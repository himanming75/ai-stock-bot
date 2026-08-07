[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ $Python="python" }

& $Python -m unittest `
  tools.test_decision_robustness_v31_v35 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

$Text=Get-Content .\decision_robustness_v31_v35\service.py -Raw
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
Write-Host "NO BROKER WRITE METHODS: PASS"
Write-Host "DATA QUALITY: AUDIT ONLY"
Write-Host "SIGNAL CONFLICT: OBSERVATION ONLY"
Write-Host "SENSITIVITY: ANALYTICS ONLY"
Write-Host "REPEATABILITY: ANALYTICS ONLY"
Write-Host "ROBUSTNESS GATE: ADVISORY ONLY"
Write-Host "CURRENT PAPER SESSION UNAFFECTED: PASS"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
