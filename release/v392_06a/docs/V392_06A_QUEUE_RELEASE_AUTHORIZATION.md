# V392.06A Queue Release Authorization

## Purpose

Authorize only the inspected FIFO head entry for local release-token
preparation.

## Required bindings

- V392.05A inspection result;
- current Queue canonical hash;
- current FIFO Head Entry hash;
- Dispatch ID;
- Token ID;
- Proposal ID;
- exact manual approval phrase;
- approving operator and reason;
- unexpired five-minute authorization;
- Paper-only environment.

## Replay protection

Each Release ID is single-use. Reused IDs are rejected.

## Boundary

Approval does not mutate the queue, change the entry status, execute a dispatch,
contact a broker, or submit Paper/Live orders.
