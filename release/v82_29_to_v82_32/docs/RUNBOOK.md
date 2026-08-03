
# Runbook

1. Install the bundle and run test-and-verify.
2. Ensure the Paper Session is `PAPER_SESSION_RUNNING`.
3. Authorize one scheduler tick.
4. Run the Intraday Loop without flags to inspect all gates.
5. When the state is `INTRADAY_LOOP_READY`, run with `-ExecuteLoop`.
6. If a stage fails, clear the cause and run with `-ResumeLoop`.
7. Complete the scheduler tick only after the Intraday Loop completes.
8. No broker order is submitted in this stage.
