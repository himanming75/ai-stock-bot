[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Remove-Item `
  .\runtime\paper_autonomous_daily_session\session.lock `
  -Force `
  -ErrorAction SilentlyContinue

powershell.exe `
  -NoProfile `
  -NonInteractive `
  -ExecutionPolicy Bypass `
  -File .\RUN_PAPER_AUTONOMOUS_DAILY_SESSION_DRY_RUN.ps1

exit $LASTEXITCODE
