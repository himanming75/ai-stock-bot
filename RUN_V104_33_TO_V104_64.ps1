param(
    [int]$MaxTicks = 0
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if($MaxTicks -gt 0){
    python tools\run_v104_33_to_v104_64.py --max-ticks $MaxTicks
}
else{
    python tools\run_v104_33_to_v104_64.py
}

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
