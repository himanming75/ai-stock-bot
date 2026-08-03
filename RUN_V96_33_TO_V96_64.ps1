param([string]$CloseDate="")
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$argsList=@()
if($CloseDate){
    $argsList+="--close-date"
    $argsList+=$CloseDate
}

python tools\run_v96_33_to_v96_64.py @argsList
if($LASTEXITCODE-ne 0){
    exit $LASTEXITCODE
}
