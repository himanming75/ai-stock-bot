# Broker Integration V2.1.19 — Manual Approval Record & Expiration Guard

Base commit: `e6a41503`

## Purpose

Record an explicit human approval for a V2.1.18 review packet without executing any order.

## Explicit approval

The user must type exactly:

`APPROVE_SANDBOX_REVIEW`

This records approval evidence only.

## Packet binding

The complete V2.1.18 JSON review packet is canonicalized and bound to the approval using SHA-256.

If the packet changes after approval, validation fails with:

`REVIEW_PACKET_FINGERPRINT_CHANGED`

## Expiration

Default approval life:

`15 minutes`

Configurable range:

`1–120 minutes`

Expired approval is blocked with:

`APPROVAL_EXPIRED`

## One-time-use state

A new approval starts with:

- `approval_consumed = false`
- `usage_count = 0`
- `one_time_use = true`

V2.1.19 does **not** consume the approval. Consumption belongs to a later handoff stage.

## Duplicate approval guard

The same evidence key cannot receive another approval record in this stage.

## Runtime files

Approval ledger:

`runtime/manual_approval_v2_1_19/approval_ledger.jsonl`

Latest approval:

`runtime/manual_approval_v2_1_19/latest_approval.json`

## Safety boundary

V2.1.19:
- performs no market-data request
- starts no E*TRADE OAuth
- sends no Sandbox Preview
- sends no Sandbox Place
- submits zero broker orders
- does not enable automatic Sandbox execution

A valid approval can only reach:

`READY_FOR_ONE_TIME_MANUAL_SANDBOX_HANDOFF`

## Safety

PROD remains locked.
Live trading remains locked.
No profitability claim is made.
