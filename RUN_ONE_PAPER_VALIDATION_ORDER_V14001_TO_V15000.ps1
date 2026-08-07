[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if(-not (Test-Path $Python)) {
    throw "PROJECT VIRTUAL ENVIRONMENT PYTHON NOT FOUND"
}

& $Python `
    .\tools\run_v14001_to_v15000_paper_autonomous_execution.py `
    --submit-paper

exit $LASTEXITCODE