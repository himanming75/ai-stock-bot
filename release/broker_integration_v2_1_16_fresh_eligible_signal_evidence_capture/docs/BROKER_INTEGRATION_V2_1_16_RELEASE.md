# Broker Integration V2.1.16 — Fresh Eligible Signal Evidence Capture

Base commit: `d179ddde`

## Purpose

Create a dedicated evidence ledger for actual eligible BUY/SELL signals that have already passed the V2.1.15 observation path.

## No duplicate observer

V2.1.16 does **not** create another market observation loop.

It reads the existing V2.1.15 ledger:

`runtime/freshness_guarded_persistent_observer_v2_1_15/observation_ledger.jsonl`

and captures only rows where:

- `observer_state == OBSERVED_FRESH`
- `eligible_signal_captured == true`
- `eligible_signal_count > 0`

## Evidence ledger

Captured evidence is written to:

`runtime/fresh_eligible_signal_evidence_v2_1_16/eligible_signal_evidence.jsonl`

Latest evidence is written to:

`runtime/fresh_eligible_signal_evidence_v2_1_16/latest_eligible_signal_evidence.json`

## Deduplication

V2.1.16 uses the V2.1.15 `snapshot_fingerprint` as the evidence key.

Re-running the capture command does not duplicate an already-recorded signal snapshot.

## Evidence fields

Evidence includes:
- observation time
- source iteration
- canonical gate alignment
- session/freshness result
- eligible signal count
- symbol
- side
- quantity
- strategy id
- source confidence where available

## Execution boundary

V2.1.16:
- performs no market-data request
- starts no E*TRADE OAuth
- sends no Sandbox Preview
- sends no Sandbox Place
- submits zero broker orders

Evidence does not authorize execution.

## Safety

PROD remains locked.
Live trading remains locked.
No profitability claim is made.
