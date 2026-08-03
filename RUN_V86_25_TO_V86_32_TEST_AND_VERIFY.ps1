$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v86_25_to_v86_32.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_ai_explainability_v86_25_to_v86_32 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V86_25_TO_V86_32_AI_EXPLAINABILITY.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_ai_explainability_v86_25_to_v86_32.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V86.25-V86.32 TEST AND VERIFY PASS"
