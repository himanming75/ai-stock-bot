# Paper Pilot Automation Runbook

1. Copy the automation policy example.
2. Run test and verify.
3. Before Pilot start, WAIT_PILOT_START is expected.
4. Refresh the actual Paper snapshot separately with explicit `-EnableNetwork`.
5. Run the Pilot heartbeat, performance collector, and risk monitor separately.
6. Re-run this automation foundation to inspect the consolidated gate.
7. `-AuthorizeCycle` writes local authorization only; it executes no child script.
