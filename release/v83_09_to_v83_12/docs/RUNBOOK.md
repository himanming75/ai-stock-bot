
# Runbook

1. Install the bundle and run test-and-verify.
2. Ensure the Orchestrator reports `ORCHESTRATOR_ACTION_READY`.
3. Authorize the action in V83.01-V83.04.
4. Execute the action successfully in V83.05-V83.08.
5. Run this stage without flags and verify `CONTROLLED_CYCLE_READY`.
6. Run once with `-ExecuteCycle`.
7. If a stage fails, correct the source state and use `-ResumeCycle`.
8. Use `-ClearCycleLock` only after investigating an interrupted cycle.
9. The cycle does not auto-repeat and does not submit broker orders.
