# R6 Runtime Session Manager

R6 wraps the validated R5 runtime configuration in an operator-controlled
session lifecycle.

Prepared features:

- unique Session ID;
- single-instance session lock;
- immutable profile/runtime snapshot hash;
- heartbeat;
- checkpoint;
- session ledger;
- stop-request marker;
- crash/resume preview;
- Paper and Live gates.

Resume never automatically replays an order and never restarts the broker.
A new operator-reviewed session is required after interruption.

This preparation performs zero broker network activity and submits zero orders.
