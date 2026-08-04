param(
    [string]$SessionDate = ""
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if([string]::IsNullOrWhiteSpace($SessionDate)){
    python tools\run_v106_01_to_v106_32.py
}
else{
    python tools\run_v106_01_to_v106_32.py --session-date $SessionDate
}

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
