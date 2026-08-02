# OP4.05-OP4.08 Paper Pilot Session Monitor

- OP4.05 Write deterministic Pilot heartbeat ticks
- OP4.06 Detect missing or stale heartbeat timeout
- OP4.07 Produce Pilot session health state
- OP4.08 Write a local controlled-stop requirement

Controlled stop changes local state only. It does not cancel orders, close
positions, or send any broker request.
