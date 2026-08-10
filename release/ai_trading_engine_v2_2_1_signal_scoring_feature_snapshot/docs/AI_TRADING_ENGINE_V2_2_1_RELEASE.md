# AI Trading Engine V2.2.1 — Signal Scoring + Feature Snapshot

Base commit: `c9639d6b`.

## Purpose

Start Phase 2 AI-engine improvement without changing the currently running
Paper execution path.

V2.2.1 reads the existing canonical real-market multi-timeframe shadow output
produced by `multi_timeframe_ai.engine.analyze_symbol` and the current selector
contract from `paper_autonomous_execution.signals.select_candidate`.

## Added

- full per-timeframe feature snapshot ledger;
- existing selector eligibility explanation;
- explicit reasons such as HOLD, low confidence, or low reward/risk;
- observational shadow quality score;
- deterministic snapshot fingerprint and deduplication;
- latest JSON snapshot plus historical JSONL ledger.

## Not changed

- canonical AI calculations;
- confidence threshold;
- reward/risk threshold;
- Paper candidate selector;
- entry / exit logic;
- position sizing;
- broker integration;
- V2.1.31 Paper operation.

The V2.2.1 quality score is diagnostics-only and cannot submit an order.

Install/tests perform no broker network calls and submit zero Paper/Live orders.
