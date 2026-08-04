$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$policyPath = ".\release\v306_01_to_v310_64\config\real_paper_micro_order_policy.json"
$tokenPath = ".\release\v306_01_to_v310_64\control\one_time_micro_order_token.json"
$typed = Read-Host "Type ENABLE_ONE_DOLLAR_PAPER_ORDER"
if($typed -ne "ENABLE_ONE_DOLLAR_PAPER_ORDER"){
  throw "Confirmation phrase did not match."
}
$policy = Get-Content $policyPath -Raw | ConvertFrom-Json
$policy.micro_order_enabled = $true
$policy | ConvertTo-Json -Depth 20 | Set-Content $policyPath -Encoding UTF8
@{
  enabled = $true
  consumed = $false
  phrase = "ENABLE_ONE_DOLLAR_PAPER_ORDER"
  client_order_id = ""
  created_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content $tokenPath -Encoding UTF8
Write-Host "One-time $1 Alpaca Paper order token enabled."
Write-Host "Live trading remains disabled."
