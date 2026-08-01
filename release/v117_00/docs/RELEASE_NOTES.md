# Release Notes

V116.01–V117.00 adds operational stability controls around the Paper runtime.

The controller isolates repeated failures, applies bounded backoff, opens a circuit breaker after three consecutive failures, attempts recovery, monitors heartbeat age, and guarantees recovery-save-before-stop shutdown ordering.
