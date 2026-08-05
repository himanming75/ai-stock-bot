# L5 Live Autonomous Runtime Preparation

L5 prepares the future Live autonomous runtime with:

- single-instance runtime lock;
- duplicate-cycle protection;
- market-open gate;
- L1, L2 Actual, L3 Actual, L4 Actual, and P5 Actual gates;
- heartbeat;
- checkpoint;
- cycle ledger;
- fail-closed behavior;
- graceful shutdown support.

Actual Live runtime remains blocked until all prior Actual qualifications pass.
Installation and offline qualification use zero broker network access and submit
zero orders.
