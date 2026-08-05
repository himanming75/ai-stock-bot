# Automation Watchdog and Restart Recovery

The watchdog supervises the Paper Automation Controller.

Included:

- controller process execution
- nonzero exit detection
- bounded restart attempts
- restart backoff
- crash-loop blocking
- stale controller-lock cleanup
- checkpoint heartbeat inspection
- market-close idle behavior
- append-only watchdog ledger
- atomic watchdog state
- restart history
- stdout and stderr evidence
- Paper and Live submission hard-disabled

The watchdog never enables broker writes. Controller V1 remains read-only.
