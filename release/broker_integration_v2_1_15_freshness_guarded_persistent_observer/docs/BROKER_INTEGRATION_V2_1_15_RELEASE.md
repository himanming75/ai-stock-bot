# Broker Integration V2.1.15 — Freshness-Guarded Persistent Observer

Base commit: `760ffaeb`

## Purpose

Integrate:
- V2.1.13 persistent observation policy/ledger behavior
- V2.1.14 market-session clock guard
- V2.1.14 freshness-aware runtime

without duplicating the existing market-data, signal, gate, or order engines.

## Key behavior

### Outside regular clock window

The observer records:

`WAITING_SESSION`

and does **not** call the V2.1.14 runtime.

Therefore the Alpaca REST bootstrap is skipped for that iteration.

### Inside regular clock window

The observer calls the existing V2.1.14 freshness-aware runtime.

If bars are stale/missing/future-dated:

`STALE_BLOCK`

Eligible capture is prohibited.

If all required bars are fresh:

`OBSERVED_FRESH`

Only then can an eligible signal be captured into the evidence ledger.

## Runtime ledger

`runtime/freshness_guarded_persistent_observer_v2_1_15/observation_ledger.jsonl`

Latest snapshot:

`runtime/freshness_guarded_persistent_observer_v2_1_15/latest_snapshot.json`

## Safety boundary

V2.1.15 never:
- starts E*TRADE OAuth
- sends Sandbox Preview
- sends Sandbox Place
- submits a broker order

A captured eligible signal is evidence only.

## Existing safeguards retained

- bounded observation count
- unchanged-state stop guard
- V2.1.14 freshness policy
- canonical gate inside V2.1.12/V2.1.14
- PROD locked
- live trading locked
- no profitability claim
