# V83.61-V83.64 Crash Recovery & Restart Continuation

## V83.61 Saved-State Inspection
Reads the full-cycle result and active cycle/dispatch/runner/retry/approval locks.

## V83.62 Recovery Decision
Produces one supervised decision: resume saved state, abort incomplete cycle,
clear stale locks, require manual intervention, or no action.

## V83.63 Recovery Application
Applies only an explicitly requested local recovery action. Automatic resume is
disabled. Recovery snapshots and an append-only ledger are written.

## V83.64 Dashboard and Verification
Publishes active locks, stale locks, decision, and applied state.

Paper-only. No broker write, order submission, live trading, or network write.
