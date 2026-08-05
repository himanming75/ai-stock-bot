# V392.09A Local Dispatch Engine Preparation

## Purpose

Create an immutable local Dispatch Context from the approved V392.08A release
record and the original V392.03A order payload.

## Context bindings

- Dispatch ID;
- Proposal ID;
- Authorization Token ID;
- Release Token ID;
- Risk Policy Hash;
- Order Payload Hash;
- Release Record Hash;
- Canonical Context Hash;
- Paper-only target.

## Replay protection

Each Context ID can be created only once.

## Boundary

The Dispatch Context only prepares the next local paper dispatch engine stage.
No broker adapter is enabled, the queue is not mutated, and no Paper/Live order
is submitted.
