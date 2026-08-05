# V392.08A Local Dispatch Release Gate

## Purpose

Validate an accepted V392.07A Release Token against the current FIFO Queue Head
and create a local Release Record for the next engine-preparation stage.

## Controls

- Release Token Gate must be open;
- current queue must exist and be unlocked;
- FIFO Head must remain sequence 1 and `QUEUED`;
- Dispatch ID and Proposal ID must match;
- Queue and Head Entry hash checks must have passed;
- Dispatch ID may be released only once;
- target remains Paper-only.

## Boundary

This stage does not mutate the queue, change entry status, execute a dispatch,
contact a broker, or submit Paper/Live orders.
