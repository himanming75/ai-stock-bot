$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "R2 runtime wrapper is DISABLED."
Write-Host "Production release approval is required."

$Certificate = Join-Path $Root `
  "release\r1_production_deployment_preparation\actual\production_release_certificate.json"

if (-not (Test-Path $Certificate)) {
    throw "R1 production release certificate is missing."
}

$Result = Get-Content $Certificate -Raw | ConvertFrom-Json

if (
    $Result.eligible -ne $true -or
    $Result.production_release_allowed -ne $true
) {
    throw "R2 runtime blocked by R1 production release gate."
}

throw "R2 actual runtime activation is intentionally not implemented in preparation mode."
