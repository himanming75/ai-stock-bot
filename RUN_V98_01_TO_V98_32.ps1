param([switch]$Force)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$argsList=@()
if($Force){$argsList+="--force"}

python tools\run_v98_01_to_v98_32.py @argsList
if($LASTEXITCODE-ne 0){
    exit $LASTEXITCODE
}
