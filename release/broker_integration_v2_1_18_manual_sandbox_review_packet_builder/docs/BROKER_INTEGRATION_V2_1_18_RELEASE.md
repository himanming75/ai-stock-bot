# Broker Integration V2.1.18 — Manual Sandbox Review Packet Builder

Base commit: `a1d860fc`

## Purpose

Build human-readable review packets from V2.1.17 rows that are already:

`READY_FOR_MANUAL_SANDBOX_REVIEW`

## Output

For each ready evidence key:

- JSON review packet
- Markdown review packet
- Manual checklist
- Packet index record

Runtime directory:

`runtime/manual_sandbox_review_packets_v2_1_18/`

## Review packet content

- evidence key
- observation time
- qualification result
- canonical minimum confidence
- symbol
- side
- quantity
- strategy id
- source confidence
- manual checklist
- safety lock state

## Critical boundary

This stage does not record approval.

It does not:
- fetch market data
- start E*TRADE OAuth
- send Preview
- send Place
- submit broker orders

`AWAITING_MANUAL_REVIEW` is the only packet state created here.

## Safety

Automatic Sandbox execution remains disabled.
PROD remains locked.
Live trading remains locked.
No profitability claim is made.
