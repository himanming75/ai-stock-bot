# Multi-Day Paper Validation Runbook

1. Copy the validation policy example.
2. Run test and verify.
3. Before Pilot start, WAIT_PILOT_START is expected.
4. After Pilot start, refresh Snapshot, Heartbeat, Performance, Risk, and Automation.
5. Record exactly one validation day with `-RecordValidationDay`.
6. The same validation date cannot be recorded twice.
7. Continue until minimum days and consecutive healthy-day requirements are met.
