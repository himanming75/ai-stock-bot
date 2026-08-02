# Controlled Paper Pilot Runbook

1. Refresh the actual Paper snapshot.
2. Run test and verify; it previews the pilot gate only.
3. Review open-order and recovery status.
4. Do not start the pilot until open orders are zero and recovery is clear.
5. Start with `-StartPilot` only after all gates are ready.
6. A second active pilot is blocked by the runtime lock.
