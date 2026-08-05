# V392.03A Dispatch Preparation Gate

## Purpose

Convert an accepted V392.02A token-gate result into a local dispatch
preparation record without contacting a broker.

## Binding controls

- Dispatch ID;
- Token ID;
- Proposal ID;
- Risk Policy hash;
- Canonical Order Payload SHA-256 hash;
- Paper-only target;
- Broker submission disabled;
- Automatic dispatch disabled.

## Replay protection

A Dispatch ID may be queued only once. Duplicate IDs are rejected.

## Boundary

This stage creates only a local queue-preparation record. Dispatch execution,
broker writes, and Paper/Live submissions remain disabled.
