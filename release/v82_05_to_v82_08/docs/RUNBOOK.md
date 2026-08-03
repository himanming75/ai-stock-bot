
# Runbook

1. Install the bundle into the existing repository.
2. Run the test-and-verify script.
3. Use `-WriteHeartbeat` to refresh the local scheduler heartbeat.
4. Use `-AuthorizeNextCycle` only after the cycle interval is due.
5. The scheduler only writes local authorization state. It never submits an order.
