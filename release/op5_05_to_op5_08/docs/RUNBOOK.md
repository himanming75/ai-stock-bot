# Validation Analytics Runbook

1. Copy the analytics policy example.
2. Run test and verify.
3. With zero validation records, WAIT_VALIDATION_DATA is expected.
4. Record validation days through OP5.01-OP5.04.
5. Re-run Analytics after each new validation day.
6. Analytics becomes complete only after the Validation Gate clears.
