# Broker Integration V2.1.17 — Evidence Qualification & Sandbox Readiness Gate

Base commit: `3ace89b4`

## Purpose

Qualify V2.1.16 fresh eligible-signal evidence for **manual E*TRADE Sandbox review**.

This stage does not execute any order.

## Input

V2.1.16 evidence ledger:

`runtime/fresh_eligible_signal_evidence_v2_1_16/eligible_signal_evidence.jsonl`

## Qualification requirements

An evidence row is READY only when all of the following are true:

- observer state is `OBSERVED_FRESH`
- canonical gate alignment is true
- signal capture was allowed
- all bars were fresh
- freshness status is `PASS_REGULAR_WINDOW_FRESH_BARS`
- eligible signal count is 1–3
- signal count matches the evidence payload
- side is BUY or SELL
- symbol is valid
- quantity is numeric and greater than zero
- source confidence is at least the repository canonical floor `0.60`
- no duplicate signal exists inside the evidence
- evidence-only flag is true
- source evidence shows zero broker orders
- PROD remains false
- live trading remains false

## Result

Qualified evidence:

`READY_FOR_MANUAL_SANDBOX_REVIEW`

Rejected evidence:

`NOT_READY`

READY does **not** authorize automatic execution.

## Qualification ledger

`runtime/sandbox_readiness_gate_v2_1_17/qualification_ledger.jsonl`

Latest result:

`runtime/sandbox_readiness_gate_v2_1_17/latest_qualification.json`

The evidence key is used for qualification deduplication.

## Execution boundary

V2.1.17:
- performs no market-data request
- starts no E*TRADE OAuth
- sends no Sandbox Preview
- sends no Sandbox Place
- submits zero broker orders

## Safety

Manual Sandbox review is always required.
Automatic Sandbox execution remains disabled.
PROD remains locked.
Live trading remains locked.
No profitability claim is made.
