param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("paper", "live")]
    [string]$Mode,
    [string]$Reason = "OPERATOR_ROTATION"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Actual = Join-Path $Root `
  "release\r3_secure_credential_storage\actual"
$MetadataPath = Join-Path $Actual "$($Mode)_vault_metadata.json"

$OldFingerprint = ""
if (Test-Path $MetadataPath) {
    $OldMetadata = Get-Content $MetadataPath -Raw | ConvertFrom-Json
    $OldFingerprint = $OldMetadata.key_fingerprint
}

& (Join-Path $Root "CREATE_R3_CREDENTIAL_VAULT.ps1") -Mode $Mode

$NewMetadata = Get-Content $MetadataPath -Raw | ConvertFrom-Json

$Record = @{
    stage = "R3_CREDENTIAL_ROTATION"
    mode = $Mode
    rotated_at = [DateTimeOffset]::UtcNow.ToString("o")
    old_key_fingerprint = $OldFingerprint
    new_key_fingerprint = $NewMetadata.key_fingerprint
    reason = $Reason
    raw_credentials_recorded = $false
}

$LedgerPath = Join-Path $Actual "credential_rotation_ledger.jsonl"
($Record | ConvertTo-Json -Compress) |
    Add-Content $LedgerPath -Encoding UTF8

Write-Host "Credential rotation recorded."
