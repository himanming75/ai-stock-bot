$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
@{
  stop_requested = $false
  reason = ""
  updated_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content `
  ".\release\v261_01_to_v265_64\control\session_stop.json" `
  -Encoding UTF8
Write-Host "Session stop request cleared."
