$ErrorActionPreference="Stop"
$Path="C:\stock-bot\runtime\ai_continuous_shadow_learning_pipeline_v2_2_8\STOP"
New-Item -ItemType Directory -Force (Split-Path -Parent $Path) | Out-Null
Set-Content -Path $Path -Value "STOP_REQUESTED" -Encoding ASCII
Write-Host "V2.2.8 STOP FILE WRITTEN:"
Write-Host $Path
