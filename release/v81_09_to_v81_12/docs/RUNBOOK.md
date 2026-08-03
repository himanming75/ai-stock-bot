# Runbook

1. Install the bundle into `C:\stock-bot`.
2. Confirm the policy and market-prices input files.
3. Run the test-and-verify PowerShell script.
4. While V81.05-V81.08 waits for its foundation, `WAIT_SHADOW_EXECUTION`
   is expected.
5. When a virtual fill exists, the engine updates the persistent shadow
   portfolio exactly once using `fill_id`.
6. Re-running the same fill does not double-count it.
