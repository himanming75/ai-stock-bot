# V392.11A1 Verify Hotfix

## Problem

After the first successful local simulation, the same `local_execution_id` is
correctly blocked by replay protection. In that blocked branch,
`actual_broker_orders_submitted` was absent. The verifier interpreted the
missing field as `None`, causing `broker_orders_zero` to fail.

## Fix

- blocked simulator results now explicitly include
  `actual_broker_orders_submitted: 0`;
- the verifier defaults a missing broker-order count to zero for compatibility
  with already-written replay-blocked results;
- an approved result still requires a Fill Event;
- a blocked result may contain an empty Fill Event;
- blocked results must be explained by replay detection or another failed
  validation check;
- any nonzero broker-order count still fails verification.

Replay protection remains unchanged.
