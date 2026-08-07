[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python `
    .\tools\run_smart_safe_trading_guard.py `
    --repository-root $PSScriptRoot

exit $LASTEXITCODE
