
# Runbook

1. Install and run test-and-verify.
2. Update `market_calendar_state.json` from the local market-session source.
3. Run without flags to inspect the schedule gates.
4. When `SCHEDULED_RUN_READY`, run once with `-AuthorizeRun`.
5. The next stage will dispatch the authorized Supervised Runner.
6. After it completes, run with `-CompleteRun`.
7. Use `-ClearScheduleLock` only after investigating an interrupted run.
8. Windows Task installation and broker orders remain disabled.
