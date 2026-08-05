param(
    [ValidateSet("paper", "live", "all")]
    [string]$Mode = "all"
)

if ($Mode -eq "paper" -or $Mode -eq "all") {
    Remove-Item Env:APCA_API_KEY_ID -ErrorAction SilentlyContinue
    Remove-Item Env:APCA_API_SECRET_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:APCA_API_BASE_URL -ErrorAction SilentlyContinue
}

if ($Mode -eq "live" -or $Mode -eq "all") {
    Remove-Item Env:LIVE_APCA_API_KEY_ID -ErrorAction SilentlyContinue
    Remove-Item Env:LIVE_APCA_API_SECRET_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:LIVE_APCA_API_BASE_URL -ErrorAction SilentlyContinue
}

Write-Host "$($Mode.ToUpper()) credential environment cleared."
