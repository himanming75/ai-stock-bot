
param(
    [switch]$EmergencyStop,
    [switch]$RequestRecovery
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V82.13-V82.16 SHADOW RISK CONTROLLER ==="
Write-Host "Local risk gates only. No network or broker orders."

$argsList = @()
if ($EmergencyStop) {
    $argsList += "--emergency-stop"
}
if ($RequestRecovery) {
    $argsList += "--request-recovery"
}

python tools/run_shadow_risk_controller_v82_13_to_v82_16.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.13-V82.16 COMPLETE"
