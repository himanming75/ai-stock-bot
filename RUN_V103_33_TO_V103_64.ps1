param(
    [string]$StartDate = "",
    [int]$SessionCount = 0
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$ArgsList=@()
if(-not [string]::IsNullOrWhiteSpace($StartDate)){
    $ArgsList+=@("--start-date",$StartDate)
}
if($SessionCount -gt 0){
    $ArgsList+=@("--session-count",$SessionCount)
}

python tools\run_v103_33_to_v103_64.py @ArgsList
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
