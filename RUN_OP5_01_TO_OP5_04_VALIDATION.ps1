param(
    [switch]$RecordValidationDay,
    [string]$ValidationDate = ""
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP5.01-OP5.04 MULTI-DAY PAPER VALIDATION ==="
Write-Host "One local validation-day record maximum. No broker requests or orders."

$argsList=@(
    "tools/run_multi_day_paper_validation_op5_01_to_op5_04.py",
    "--repository-root",
    "."
)
if($RecordValidationDay){
    $argsList+="--record-validation-day"
}
if(-not [string]::IsNullOrWhiteSpace($ValidationDate)){
    $argsList+=@("--validation-date",$ValidationDate)
}

python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP5.01-OP5.04 COMPLETE"
