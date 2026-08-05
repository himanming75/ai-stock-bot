param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("paper", "live")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Actual = Join-Path $Root `
  "release\r3_secure_credential_storage\actual"

$PayloadPath = Join-Path $Actual "$($Mode)_credentials.dpapi"
$MetadataPath = Join-Path $Actual "$($Mode)_vault_metadata.json"

Write-Host "This removes the encrypted $Mode vault from this computer."
$Confirm = Read-Host 'Type REMOVE to continue'

if ($Confirm -ne "REMOVE") {
    throw "Vault removal canceled."
}

Remove-Item $PayloadPath -Force -ErrorAction SilentlyContinue
Remove-Item $MetadataPath -Force -ErrorAction SilentlyContinue

Write-Host "$($Mode.ToUpper()) vault removed."
