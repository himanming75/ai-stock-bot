$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_v8801_to_v9000_paper_command_center_certification.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
