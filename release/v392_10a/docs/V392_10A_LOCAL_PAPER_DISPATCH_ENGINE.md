# V392.10A Local Paper Dispatch Engine

## Purpose

Accept a valid V392.09A Dispatch Context into a local-only paper dispatch state
machine.

## Output state

A valid context creates a local order with:

`submission_state = ACCEPTED_FOR_SIMULATION`

This is not a broker order and is not submitted to Alpaca or any external
service.

## Validation

- V392.09A preparation result;
- Context ID and Context Hash;
- Dispatch and Proposal IDs;
- Risk Policy Hash;
- Order Payload Hash;
- Paper-only environment;
- allowed side, order type, and time-in-force;
- positive estimated notional;
- single-use Context ID.

## Boundary

- broker adapter disabled;
- broker network disabled;
- queue mutation disabled;
- Paper submission disabled;
- Live submission disabled;
- actual submitted orders remain zero.

The next stage is the local Paper Execution Simulator.
