# AI Trading Engine V2.2.2 — Outcome Labeling + Feature/Trade Binding

Base commit: `ff453252`.

## Purpose

Create the first training/evaluation dataset that joins pre-entry AI features
to actual completed Alpaca Paper outcomes.

## Sources

Feature source:
- V2.2.1 `feature_snapshot_ledger.jsonl`

Outcome source:
- V2.1.27 `completed_round_trips.jsonl`

V2.1.27 remains the source of truth for actual entry/exit fills, holding time,
gross fill-based P&L, return percentage, and exit reason.

## Binding policy

For each completed trade:
1. require the same symbol;
2. use only feature snapshots at or before actual entry fill time;
3. choose the closest preceding snapshot;
4. require feature lag <= 1800 seconds (30 minutes);
5. otherwise preserve the trade in an unbound-outcome ledger.

Future snapshots are never used for an earlier trade.

## Labels

- positive fill P&L -> WIN
- negative fill P&L -> LOSS
- zero fill P&L -> FLAT

P&L and return are copied from V2.1.27 and are NOT recomputed.

## Safety

V2.2.2:
- does not modify the canonical feature engine;
- does not modify the execution selector;
- performs no broker network calls;
- submits zero Paper orders;
- submits zero Live orders.

This dataset is for later calibration/model evaluation only.
