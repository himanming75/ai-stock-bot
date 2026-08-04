$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "Starting AI Stock Bot Web Controller..."
Write-Host "Open http://127.0.0.1:8765"
python tools\run_v141_01_to_v145_64.py --host 127.0.0.1 --port 8765
