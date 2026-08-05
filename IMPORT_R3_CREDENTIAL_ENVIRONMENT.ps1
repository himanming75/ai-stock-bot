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

if (-not (Test-Path $PayloadPath)) {
    throw "Encrypted credential payload is missing: $PayloadPath"
}
if (-not (Test-Path $MetadataPath)) {
    throw "Credential metadata is missing: $MetadataPath"
}

$Metadata = Get-Content $MetadataPath -Raw | ConvertFrom-Json
$Payload = Get-Content $PayloadPath -Raw | ConvertFrom-Json

if (
    $Metadata.encryption_provider -ne
    "WINDOWS_DPAPI_CURRENT_USER_SECURESTRING"
) {
    throw "Unsupported encryption provider."
}
if (
    $Payload.encryption_provider -ne
    "WINDOWS_DPAPI_CURRENT_USER_SECURESTRING"
) {
    throw "Encrypted payload provider mismatch."
}

if ($Mode -eq "paper") {
    if ($Metadata.base_url -ne "https://paper-api.alpaca.markets") {
        throw "Paper endpoint mismatch."
    }
} else {
    if ($Metadata.base_url -ne "https://api.alpaca.markets") {
        throw "Live endpoint mismatch."
    }

    $CertificatePath = Join-Path $Root `
      "release\r1_production_deployment_preparation\actual\production_release_certificate.json"

    if (-not (Test-Path $CertificatePath)) {
        throw "R1 production certificate is missing."
    }

    $Certificate = Get-Content $CertificatePath -Raw | ConvertFrom-Json
    if (
        $Certificate.eligible -ne $true -or
        $Certificate.production_release_allowed -ne $true
    ) {
        throw "Live credential bootstrap blocked by R1 release gate."
    }
}

if ($Payload.mode -ne $Mode) {
    throw "Credential mode mismatch."
}
if ($Payload.base_url -ne $Metadata.base_url) {
    throw "Credential endpoint mismatch."
}

$KeySecure = $Payload.encrypted_api_key | ConvertTo-SecureString
$SecretSecure = $Payload.encrypted_secret_key | ConvertTo-SecureString

$KeyPtr = [IntPtr]::Zero
$SecretPtr = [IntPtr]::Zero
$KeyPlain = $null
$SecretPlain = $null

try {
    $KeyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($KeySecure)
    $SecretPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecretSecure)

    $KeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($KeyPtr)
    $SecretPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($SecretPtr)

    if ($Mode -eq "paper") {
        $env:APCA_API_KEY_ID = $KeyPlain
        $env:APCA_API_SECRET_KEY = $SecretPlain
        $env:APCA_API_BASE_URL = $Payload.base_url
    } else {
        $env:LIVE_APCA_API_KEY_ID = $KeyPlain
        $env:LIVE_APCA_API_SECRET_KEY = $SecretPlain
        $env:LIVE_APCA_API_BASE_URL = $Payload.base_url
    }

    Write-Host "$($Mode.ToUpper()) credential environment loaded."
    Write-Host "Endpoint:" $Payload.base_url
    Write-Host "Key fingerprint:" $Metadata.key_fingerprint
    Write-Host "Raw credentials were not printed."
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
    $KeySecure = $null
    $SecretSecure = $null
    $Payload = $null
}
