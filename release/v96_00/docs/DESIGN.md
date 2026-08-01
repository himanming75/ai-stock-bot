# V95.01-V96.00 Fast Track Design

Adds a tightly gated, single-order Alpaca Paper execution path while keeping the standard pipeline fully offline.

The actual transport is isolated in a separate runner and requires all environment opt-ins, Paper credentials, a clear kill switch, and an exact manual confirmation phrase. The default RUN script executes fixtures only and produces zero network requests and zero submitted orders.
