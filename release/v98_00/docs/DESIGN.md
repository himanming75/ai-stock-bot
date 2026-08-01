# V97.01-V98.00 Fast Track Design

Adds controlled Paper session lifecycle management: create, start, heartbeat, duplicate-session guard, checkpoint resume, consume, close, recovery, rollback, audit ledger, manifest, and RC2 certification.

The standard pipeline is offline. The separate actual session runner starts a gated session but submits no order by itself.
