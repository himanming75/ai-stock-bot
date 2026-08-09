$ErrorActionPreference="Stop"
$Path="C:\stock-bot\runtime\etrade_sandbox_multi_cycle_v2_1_4\KILL_SWITCH"
New-Item -ItemType Directory -Force (Split-Path $Path) | Out-Null
Set-Content -Path $Path -Value "STOP" -Encoding ASCII
Write-Host "V2.1.4 KILL SWITCH: ON"
Write-Host $Path
