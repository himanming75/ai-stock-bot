
# Runbook

1. Install the bundle and run test-and-verify.
2. Complete Daily Certification in V82.33-V82.36.
3. Prepare the next trading day in V82.33-V82.36.
4. Run without flags and wait for `MULTI_DAY_ROLLOVER_READY`.
5. Run with `-ExecuteRollover` once.
6. Do not repeat rollover for the same date.
7. `-ResetRuntime` clears only the local multi-day runtime state.
8. This stage does not automatically start the next Paper Session.
