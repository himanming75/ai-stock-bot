# P4 Autonomous Paper Runtime

P4 creates one autonomous runtime around the canonical P1–P3 path.

## Runtime cycle

1. acquire Single-Instance Lock;
2. reserve a deterministic cycle;
3. read Market Clock;
4. read Kill Switch;
5. verify P2 and P3 actual validation;
6. run AI, allocation, risk, authorization, P2 execution, and P3 sync;
7. Fail-Closed on any error or reconciliation drift;
8. write heartbeat and checkpoint;
9. wait for the next cycle;
10. release the lock on normal or exceptional shutdown.

## Included operations

- Single-Instance Lock;
- duplicate-cycle protection;
- Market Open gate;
- P2/P3 actual-validation gate;
- Kill Switch gate;
- disk-space health check;
- heartbeat;
- checkpoint;
- cycle registry;
- cycle ledger;
- Fail-Closed cycle result;
- restart-safe state files;
- graceful lock release.

## Current qualification

Installation performs only a three-cycle Offline qualification. Actual autonomous
Paper execution remains blocked until P2 and P3 actual-validation records exist.
P4 does not submit an actual order during installation.
