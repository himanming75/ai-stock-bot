# Paper Performance Collector Runbook

1. Copy the performance policy example.
2. Run test and verify. Before Pilot start, WAIT_PILOT_START is expected.
3. After Pilot start, refresh the actual Paper snapshot.
4. Run with `-CollectSnapshot` to append one equity sample.
5. Do not run more frequently than the chosen operating cadence.
6. Add realized trade records to the local trade-performance ledger only after
   lifecycle reconciliation confirms the close.
