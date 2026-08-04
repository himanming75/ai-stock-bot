$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$path = ".\release\v261_01_to_v265_64\config\session_runner_policy.json"
$value = Get-Content $path -Raw | ConvertFrom-Json
$value.session_runner_enabled = $false
$value.allow_real_paper_network = $false
$value | ConvertTo-Json -Depth 20 | Set-Content $path -Encoding UTF8
Write-Host "Paper Session Runner disabled."
