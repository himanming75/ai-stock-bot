# Operations Bundle

This bundle develops shared operational functions in parallel while actual
Paper validation is pending.

Included:

- read-only local dashboard;
- runtime heartbeat and checkpoint display;
- P2/P3/P4 actual-validation status;
- Kill Switch display;
- recent orders, Fills, Drift, and operations events;
- JSONL structured logging with credential redaction;
- one-shot health monitoring;
- disk-space checks;
- Paper/Live mode display;
- L1 Live Safety Boundary preparation.

The L1 code is preparation only. It cannot enable Live network access, Live
writes, or Live order submission. Actual Live development remains gated behind
actual Paper completion.
