# R3 Secure Credential Storage / Environment Bootstrap

R3 stores broker credentials with Windows DPAPI CurrentUser encryption.

Properties:

- Paper and Live credentials are stored separately.
- Encrypted payloads use `.dpapi` files.
- Metadata stores fingerprints only, never raw keys or secrets.
- Decryption is restricted to the same Windows user account.
- Paper and Live endpoints are enforced by mode.
- Live environment bootstrap is blocked until R1 Production Release approval.
- Credentials are loaded only into the current PowerShell process environment.
- Secure clear removes environment variables after use.
- Rotation records contain fingerprints only.

The installer creates no vault and stores no actual credential.
