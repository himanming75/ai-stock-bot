# AI Trading Engine V2.2.4 — Threshold Calibration + Challenger Policy Builder

Base commit: `81628f25`.

## Purpose

Generate shadow-only Challenger threshold policies while leaving the current
Champion execution selector unchanged.

## Champion

Current baseline remains:

- minimum confidence: 0.75
- minimum reward/risk: 1.00

V2.2.4 does not modify those values in Paper execution.

## Challenger search

Global grid:

- confidence: 0.70, 0.75, 0.80, 0.85, 0.90
- reward/risk: 0.90, 1.00, 1.15, 1.25, 1.50

25 global combinations are evaluated against V2.2.2 labeled outcomes.

Regime-specific candidates are also generated when a regime has at least
5 labeled outcomes.

## Sample guard

A candidate is rankable only when at least 5 matching labeled outcomes exist.
Insufficient samples remain visible but cannot become actionable challengers.

## Ranking

Challenger ranking uses descriptive Paper outcome evidence:
- expectancy
- profit factor
- win rate
- gross P&L

The ranking score is shadow-only and is not consumed by execution.

## Outputs

- Champion policy registry
- Challenger policy registry
- global threshold candidate ranking
- regime-specific challenger candidates
- JSON report
- Markdown report
- deterministic registry SHA-256

## Safety

- Champion execution modified: FALSE
- Challenger execution: DISABLED
- Automatic promotion: DISABLED
- Execution selector modified: FALSE
- Broker network: OFF
- Paper orders: 0
- Live orders: 0
- Live trading: LOCKED
