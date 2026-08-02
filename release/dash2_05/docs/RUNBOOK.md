# DASH2.05 Runbook

1. Stop the Dashboard.
2. Merge this hotfix with overwrite enabled.
3. Run test and verify; this performs no network request.
4. Confirm Paper credentials in the current PowerShell process.
5. Run the actual snapshot refresh with `-EnableNetwork`.
6. Restart the Dashboard and use Ctrl+F5.
7. Refresh the snapshot whenever it becomes older than five minutes.
