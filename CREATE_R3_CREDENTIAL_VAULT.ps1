param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("paper", "live")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Actual = Join-Path $Root `
  "release\r3_secure_credential_storage\actual"

New-Item -ItemType Directory -Path $Actual -Force | Out-Null

if ($Mode -eq "paper") {
    $BaseUrl = "https://paper-api.alpaca.markets"
} else {
    $BaseUrl = "https://api.alpaca.markets"
}

Write-Host "=== R3 CREATE $($Mode.ToUpper()) CREDENTIAL VAULT ==="
Write-Host "Credentials will be encrypted with Windows DPAPI CurrentUser."
Write-Host "Raw values will not be printed."

$KeySecure = Read-Host "Enter API Key" -AsSecureString
$SecretSecure = Read-Host "Enter API Secret" -AsSecureString

$KeyPtr = [IntPtr]::Zero
$SecretPtr = [IntPtr]::Zero
$KeyPlain = $null
$SecretPlain = $null

try {
    $KeyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($KeySecure)
    $SecretPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecretSecure)

    $KeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($KeyPtr)
    $SecretPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($SecretPtr)

    if ([string]::IsNullOrWhiteSpace($KeyPlain)) {
        throw "API Key is empty."
    }
    if ([string]::IsNullOrWhiteSpace($SecretPlain)) {
        throw "API Secret is empty."
    }

    # ConvertFrom-SecureString without -Key uses Windows DPAPI CurrentUser.
    $EncryptedKey = $KeySecure | ConvertFrom-SecureString
    $EncryptedSecret = $SecretSecure | ConvertFrom-SecureString

    $Payload = @{
        schema_version = 2
        mode = $Mode
        base_url = $BaseUrl
        encryption_provider = "WINDOWS_DPAPI_CURRENT_USER_SECURESTRING"
        encrypted_api_key = $EncryptedKey
        encrypted_secret_key = $EncryptedSecret
        created_at = [DateTimeOffset]::UtcNow.ToString("o")
    }

    $PayloadPath = Join-Path $Actual "$($Mode)_credentials.dpapi"
    $Payload |
      ConvertTo-Json -Depth 5 |
      Set-Content $PayloadPath -Encoding UTF8

    $Sha = [Security.Cryptography.SHA256]::Create()
    try {
        $KeyHash = [BitConverter]::ToString(
            $Sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($KeyPlain))
        ).Replace("-", "").ToLower()

        $SecretHash = [BitConverter]::ToString(
            $Sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($SecretPlain))
        ).Replace("-", "").ToLower()
    }
    finally {
        $Sha.Dispose()
    }

    $Metadata = @{
        schema_version = 2
        mode = $Mode
        base_url = $BaseUrl
        encryption_provider = "WINDOWS_DPAPI_CURRENT_USER_SECURESTRING"
        encrypted_payload_file = "$($Mode)_credentials.dpapi"
        key_fingerprint = $KeyHash.Substring(0, 16)
        secret_fingerprint = $SecretHash.Substring(0, 16)
        created_at = [DateTimeOffset]::UtcNow.ToString("o")
        plaintext_credentials_stored = $false
    }

    $MetadataPath = Join-Path $Actual "$($Mode)_vault_metadata.json"
    $Metadata |
      ConvertTo-Json -Depth 5 |
      Set-Content $MetadataPath -Encoding UTF8

    Write-Host "Vault created:"
    Write-Host $PayloadPath
    Write-Host "Metadata:"
    Write-Host $MetadataPath
    Write-Host "Key fingerprint:" $Metadata.key_fingerprint
    Write-Host "Secret fingerprint:" $Metadata.secret_fingerprint
}
finally {
    if ($KeyPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($KeyPtr)
    }
    if ($SecretPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($SecretPtr)
    }
    $KeyPlain = $null
    $SecretPlain = $null
    $EncryptedKey = $null
    $EncryptedSecret = $null
    $Payload = $null
}
