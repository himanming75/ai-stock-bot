# AI Trading Engine V2.2.5 — Champion vs Challenger Shadow Comparator

Base commit: `d9ef8292`.

## Purpose

Compare Champion and Challenger threshold policies on exactly the same
V2.2.1 canonical AI feature snapshot.

## Policy sources

Preferred:
- V2.2.4 calibrated Challenger registry.

If V2.2.4 has no calibrated challengers yet because actual labeled outcomes
are still zero, V2.2.5 uses two deterministic seed challengers for
SHADOW COMPARISON ONLY:

- Seed A: confidence >= 0.70, reward/risk >= 1.15
- Seed B: confidence >= 0.80, reward/risk >= 0.90

Seed policies can never execute or promote.

## Comparison classifications

Each symbol is classified per Challenger as:

- BOTH
- CHAMPION_ONLY
- CHALLENGER_ONLY
- NEITHER

The same action, confidence, reward/risk, regime, quality score, and canonical
analysis fingerprint are preserved.

## Best shadow candidate

For diagnostics, each policy records the highest V2.2.1 shadow quality-score
symbol that passes that policy. This is observational only.

## Outputs

- comparison JSONL ledger
- latest detailed comparison JSON
- latest summary JSON
- deterministic comparison fingerprint / deduplication

## Safety

- Champion Paper execution remains unchanged.
- Challenger execution: DISABLED.
- Automatic promotion: DISABLED.
- Execution selector modified: FALSE.
- Broker network: OFF.
- Paper orders: 0.
- Live orders: 0.
- Live trading: LOCKED.
