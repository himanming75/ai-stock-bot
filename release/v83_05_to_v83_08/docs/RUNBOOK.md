
# Runbook

1. Install the bundle and run test-and-verify.
2. Authorize an Orchestrator Action in V83.01-V83.04.
3. Run the Dispatcher without flags and verify `LOCAL_ACTION_READY`.
4. Run `-ExecuteAction -DryRun` to inspect the mapped command.
5. Run `-ExecuteAction` to execute one approved local command.
6. A successful command closes the Orchestrator Action Lock.
7. Use `-ClearDispatchLock` only after investigating a failed or interrupted run.
8. Broker commands and Alpaca order writes remain disabled.
