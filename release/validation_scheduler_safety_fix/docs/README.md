# Validation Scheduler Safety Fix

Changes only the validation scheduler.

Fix 1 — No startup catch-up:
If the scheduler is first started after 07:30 or 13:20, those already-passed
slots are marked as skipped for that day rather than immediately executed.
`catch_up_missed_runs` defaults to false.

Fix 2 — Single-run lock:
Only one Validation Full Refresh may run at a time. A manual snapshot and a
scheduled refresh cannot overlap.

Fix 3 — Stale lock cleanup:
If the process that owned the run lock is gone, the stale lock may be removed
and a later validation run can proceed.

No changes to Paper trading, broker APIs, E*TRADE, AI models, strategies,
thresholds, risk, or Live trading.
