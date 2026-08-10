# AI Trading Engine V2.2.8 — Continuous Shadow Learning Pipeline

Base commit: `73c9b9c3`.

## Purpose

Automate the Phase-2 AI evidence pipeline while the existing Paper trading
process continues independently.

V2.2.8 does NOT start, stop, or alter the Paper trading engine.

## Watched inputs

The collector watches two source-of-truth inputs:

1. `runtime/real_market_multitimeframe_shadow/latest_real_market_shadow.json`
2. `runtime/final_round_trip_ledger_v2_1_27/completed_round_trips.jsonl`

A composite SHA-256 fingerprint is calculated. A new AI pipeline cycle runs
when either input changes. Unchanged inputs are skipped to avoid duplicate
processing.

## Dependency-ordered cycle

Each changed-input cycle runs:

1. V2.2.1 — feature snapshot
2. V2.2.2 — actual outcome labeling
3. V2.2.3 — performance segmentation
4. V2.2.4 — Challenger calibration
5. V2.2.5 — Champion/Challenger shadow comparison
6. V2.2.7 — Challenger-only shadow simulation
7. V2.2.6 — realized Champion/Challenger outcome comparison

This order allows newly completed actual trades to update calibration before
the next shadow comparison.

## Continuous supervisor

Default continuous settings:

- poll interval: 60 seconds
- maximum runtime: 8 hours
- first cycle: forced
- unchanged inputs: skipped
- stage exception/block: fail closed and stop supervisor
- STOP file supported

The collector is intended to run in a separate PowerShell window from the
existing V2.1.31 Paper session.

## Scorecard foundation

V2.2.8 creates a single scorecard containing:

- actual Champion labeled outcomes, wins/losses/P&L
- Challenger completed counterfactual outcomes, wins/losses/P&L
- BOTH / CHAMPION_ONLY / CHALLENGER_ONLY / NEITHER counts
- segmentation status
- calibration status/readiness
- V2.2.6 promotion-evidence readiness

The scorecard never promotes a policy.

## Safety

- Broker network from V2.2.8: OFF
- Paper orders from V2.2.8: 0
- Live orders: 0
- Challenger broker execution: DISABLED
- Automatic policy changes: DISABLED
- Automatic promotion: DISABLED
- Live trading: LOCKED

## Commands

One cycle:

`powershell -ExecutionPolicy Bypass -File .\RUN_AI_TRADING_ENGINE_V2_2_8.ps1`

Continuous collector:

`powershell -ExecutionPolicy Bypass -File .\START_V2_2_8_CONTINUOUS_SHADOW_LEARNING.ps1`

Stop collector from another terminal:

`powershell -ExecutionPolicy Bypass -File .\STOP_V2_2_8_CONTINUOUS_SHADOW_LEARNING.ps1`

Build scorecard:

`powershell -ExecutionPolicy Bypass -File .\START_V2_2_8_BUILD_SCORECARD.ps1`
