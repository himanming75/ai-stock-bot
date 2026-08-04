$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$policyPath = ".\release\v306_01_to_v310_64\config\real_paper_micro_order_policy.json"
$tokenPath = ".\release\v306_01_to_v310_64\control\one_time_micro_order_token.json"
$policy = Get-Content $policyPath -Raw | ConvertFrom-Json
$policy.micro_order_enabled = $false
$policy | ConvertTo-Json -Depth 20 | Set-Content $policyPath -Encoding UTF8
@{
  enabled = $false
  consumed = $true
  phrase = ""
  client_order_id = ""
  created_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content $tokenPath -Encoding UTF8
Write-Host "Micro Paper order validation disabled."
