param(
    [string]$CycleDate = ""
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if([string]::IsNullOrWhiteSpace($CycleDate)){
    python tools\run_v103_01_to_v103_32.py
}
else{
    python tools\run_v103_01_to_v103_32.py --cycle-date $CycleDate
}

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
