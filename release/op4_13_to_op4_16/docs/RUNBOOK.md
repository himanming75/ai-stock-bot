# Paper Risk Monitor Runbook

1. Commit OP4.09-OP4.12 before this stage.
2. Copy the risk policy example.
3. Run test and verify.
4. Before Pilot start, WAIT_PILOT_START is expected.
5. After Pilot start, refresh the actual Paper snapshot and performance report.
6. If EMERGENCY_STOP_REQUIRED appears, stop Pilot progression and investigate.
7. This stage does not perform broker-side risk actions.
