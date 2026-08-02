# V139.06 Next Order Eligibility Design

Evaluates whether a resumed autonomous cycle may proceed toward a Paper order launch.

A snapshot is required only after V139.05 reaches `CYCLE_RESUMED`.

Required conditions:

- Account active
- Trading not blocked
- Market open
- No open order
- Risk approved
- Safe mode inactive

Success creates a deterministic local eligibility token. This stage does not submit an order and performs no broker network request.
