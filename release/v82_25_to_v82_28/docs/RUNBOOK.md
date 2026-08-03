
# Runbook

1. Install the bundle and run test-and-verify.
2. Keep the Paper Session in `PAPER_SESSION_RUNNING`.
3. Use `-WriteHeartbeat` to refresh local scheduler health.
4. When the state becomes `PAPER_SCHEDULER_TICK_DUE`, use `-AuthorizeTick`.
5. After the next-stage work for that tick is complete, use `-CompleteTick`.
6. Never authorize a second tick while a tick lock is active.
7. No Alpaca order is submitted by this stage.
