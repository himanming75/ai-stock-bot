# Validation Certificate Runbook

1. Copy the certificate policy example.
2. Run test and verify.
3. Before Validation completion, WAIT_VALIDATION_COMPLETE is expected.
4. Complete Multi-Day Validation and Analytics.
5. Run with `-IssueCertificate` once.
6. Re-run without the switch to verify the existing Certificate.
7. Do not edit the Certificate after issuance; changes invalidate its seal.
