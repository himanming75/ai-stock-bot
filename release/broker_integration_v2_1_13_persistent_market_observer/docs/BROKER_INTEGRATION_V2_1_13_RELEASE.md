# Broker Integration V2.1.13 — Persistent Market Observer

Base commit: `5c611697`

## Purpose

Observe the existing V2.1.12 end-to-end plan repeatedly and capture when an eligible signal appears.

The observer does **not** execute E*TRADE Sandbox orders.

## Reuse

V2.1.13 reuses the V2.1.12 runtime plan, which already reuses:
- V2.1.8.2 Alpaca historical bootstrap
- V2.1.9 signal pipeline
- V2.1.11 canonical gate
- V2.1.10 eligible signal bridge contracts

## Observation ledger

Each observation is written to:

`runtime/persistent_market_observer_v2_1_13/observation_ledger.jsonl`

The latest snapshot is written to:

`runtime/persistent_market_observer_v2_1_13/latest_snapshot.json`

Each observation includes:
- UTC timestamp
- iteration
- bootstrap counts
- canonical-gate alignment
- eligible signal count
- eligible signal details
- snapshot fingerprint
- changed / unchanged status

## Bounded runtime

Default:
- max observations: 30
- interval: 60 seconds
- stop after 10 consecutive unchanged observations

This prevents an accidental infinite loop.

## Important execution boundary

V2.1.13:
- does not start E*TRADE OAuth
- does not Preview
- does not Place
- does not submit broker orders

A captured eligible signal remains evidence only. Actual Sandbox execution still belongs to the explicit V2.1.12 runtime.

## Safety

PROD remains locked.
Live trading remains locked.
No profitability validation is claimed.
