$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
@{
  stop_requested = $true
  reason = "USER_REQUEST"
  updated_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content `
  ".\release\v261_01_to_v265_64\control\session_stop.json" `
  -Encoding UTF8
Write-Host "Stop requested. The runner will stop after the current cycle."
