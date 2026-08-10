$ErrorActionPreference="Stop"
$Path="C:\stock-bot\runtime\ai_fast_data_acceleration_v2_2_8\STOP_LIVE_COLLECTOR"
New-Item -ItemType Directory -Force (Split-Path -Parent $Path) | Out-Null
Set-Content -Path $Path -Value "STOP_REQUESTED" -Encoding ASCII
Write-Host "V2.2.8 LIVE COLLECTOR STOP REQUESTED"
