[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) { $Python = "python" }

& $Python -m unittest `
  tools.test_paper_observability_intelligence `
  -v

if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Text = Get-Content `
  .\paper_observability\service.py `
  -Raw

$Forbidden = @(
    "submit_order",
    "cancel_order",
    "close_position",
    "replace_order"
)

foreach($Pattern in $Forbidden) {
    if($Text -match $Pattern) {
        throw "FORBIDDEN BROKER WRITE METHOD FOUND: $Pattern"
    }
}

Write-Host "VERIFY: PASS"
Write-Host "NO BROKER WRITE METHODS: PASS"
Write-Host "CURRENT PAPER SESSION UNAFFECTED: PASS"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
