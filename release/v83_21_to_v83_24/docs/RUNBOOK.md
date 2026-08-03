
# Runbook

1. Install and run test-and-verify.
2. Obtain `SCHEDULED_RUN_AUTHORIZED` from V83.17-V83.20.
3. Run without flags and verify `SCHEDULED_DISPATCH_READY`.
4. Run with `-ExecuteDispatch -DryRun`.
5. Run once with `-ExecuteDispatch`.
6. Success requires both return code 0 and `SUPERVISED_RUNNER_COMPLETE`.
7. Successful execution automatically closes the Schedule Lock.
8. Use `-ClearDispatchLock` only after investigating a failed run.
9. No Windows Task or broker order is enabled.
