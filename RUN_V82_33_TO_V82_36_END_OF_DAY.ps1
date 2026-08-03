
param(
    [switch]$CertifyDay,
    [switch]$PrepareNextDay
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V82.33-V82.36 END-OF-DAY MANAGER ==="
Write-Host "Local reporting and certification only. No broker orders."

$argsList = @()
if ($CertifyDay) {
    $argsList += "--certify-day"
}
if ($PrepareNextDay) {
    $argsList += "--prepare-next-day"
}

python tools/run_end_of_day_v82_33_to_v82_36.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.33-V82.36 COMPLETE"
