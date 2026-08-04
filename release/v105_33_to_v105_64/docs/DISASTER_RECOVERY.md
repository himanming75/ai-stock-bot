# Disaster Recovery

1. Stop all manual scripts.
2. Preserve all files under `release/*/actual`.
3. Confirm no broker write capability is enabled.
4. Run the final release verification.
5. When verification fails, use `RESTORE_TO_V105_32.ps1`.
6. Re-run V105.01-V105.32 and then V105.33-V105.64.
7. Do not delete ledgers before making a backup.
