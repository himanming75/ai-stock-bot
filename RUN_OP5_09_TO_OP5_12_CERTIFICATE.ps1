param(
    [switch]$IssueCertificate
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP5.09-OP5.12 VALIDATION CERTIFICATE ==="
Write-Host "Local certificate and SHA-256 verification only. No broker operations."

$argsList=@(
    "tools/run_validation_certificate_op5_09_to_op5_12.py",
    "--repository-root",
    "."
)
if($IssueCertificate){
    $argsList+="--issue-certificate"
}

python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP5.09-OP5.12 COMPLETE"
