param(
    [int]$IntervalSeconds=60,
    [int]$MaxCycles=10
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

$ProfilePath="release\paper_automation_controller\config\read_only_profile.runtime.json"
$Profile=Get-Content "release\paper_automation_controller\config\read_only_profile.json" -Raw | ConvertFrom-Json
$Profile.interval_seconds=$IntervalSeconds
$Profile.max_cycles=$MaxCycles
$Profile | ConvertTo-Json -Depth 10 | Set-Content $ProfilePath -Encoding UTF8

python .\tools\run_paper_automation_controller.py --profile $ProfilePath

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
