$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$path = ".\release\v261_01_to_v265_64\config\session_runner_policy.json"
$typed = Read-Host "Type ENABLE_PAPER_SESSION_RUNNER"
if($typed -ne "ENABLE_PAPER_SESSION_RUNNER"){throw "Confirmation phrase did not match."}
$value = Get-Content $path -Raw | ConvertFrom-Json
$value.session_runner_enabled = $true
$value.allow_real_paper_network = $true
$value | ConvertTo-Json -Depth 20 | Set-Content $path -Encoding UTF8
Write-Host "Paper Session Runner enabled."
Write-Host "V260 Paper submission gates must also be enabled separately."
