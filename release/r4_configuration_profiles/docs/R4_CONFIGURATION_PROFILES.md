# R4 Configuration Profile / Trading Mode Bootstrap

R4 makes trading horizon and safety parameters configurable without editing
execution code.

Prepared profiles:

- Paper ultra-short;
- Paper day;
- Paper swing;
- Paper position;
- locked Live micro profile.

Every profile includes allowed symbols, order types, maximum order notional,
daily order count, daily loss, gross exposure, symbol exposure, market gate,
Allocation flag, and Multi-Account flag.

Allocation is preserved rather than deferred or removed. Multi-Account support
is preserved in the schema even while disabled in the initial profiles.

Profile preview performs no activation, no broker network access, and no order
submission. Live profile preview remains gated by Paper completion and R1
production approval.
