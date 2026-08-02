# V139.03 Next Cycle Unlock Design

## Purpose

Validate the V139.02 handoff result and token, then create one deterministic local unlock for the next autonomous cycle.

## Input

- `release/v139_02/actual/terminal_commit_handoff_result.json`
- `release/v139_02/actual/terminal_commit_handoff_token.json` when handoff is ready

## Unlock gate

Unlock is allowed only when:

- V139.02 status is PASS
- state is HANDOFF_READY
- `next_cycle_unlock_ready=true`
- safe mode is false
- result and token handoff IDs match
- token proves terminal observation and terminal commit verification

## Outputs

- `next_cycle_unlock_result.json`
- `next_cycle_unlock_token.json` when allowed
- append-only unlock ledger on first creation
- recovery snapshot after successful or idempotent unlock

## Safety

No credentials, external broker network, order submission, or live endpoint is used.
Before a valid handoff exists, the expected result is `WAIT_HANDOFF`.
