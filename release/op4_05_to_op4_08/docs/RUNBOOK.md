# Paper Session Monitor Runbook

1. Copy the monitor policy example.
2. Run test and verify. Before Pilot start, the expected state is WAIT_PILOT_START.
3. After OP4.01 starts the Pilot, run with `-WriteHeartbeat`.
4. Repeat heartbeat manually during this stage.
5. Timeout, Emergency Stop, duplicate runtime, or `-ControlledStop` writes a
   local controlled-stop record only.
6. Broker orders and positions are never changed by this monitor.
