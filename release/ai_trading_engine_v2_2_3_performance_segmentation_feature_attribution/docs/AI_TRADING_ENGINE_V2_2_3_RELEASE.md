# AI Trading Engine V2.2.3 — Performance Segmentation + Feature Attribution

Base commit: `46725887`.

## Purpose

Turn V2.2.2 labeled Paper outcomes into descriptive performance evidence
without changing the execution selector.

## Source

- V2.2.2 `labeled_outcomes.jsonl`

No broker, market-data, or order API is called by this stage.

## Segmentation

V2.2.3 reports performance by:

- symbol
- market regime
- dominant structure
- calibrated-confidence bin
- reward/risk bin
- trend-alignment bin
- V2.2.1 shadow-quality-score bin
- exit reason
- action

## Metrics

Each segment includes:

- trades / wins / losses / flats
- win rate / loss rate
- gross fill-based P&L before fees
- average P&L
- average return
- average holding time
- gross profit
- gross loss
- profit factor
- average winner
- average loser
- expectancy per trade

## Sample guard

A segment is not considered actionable until it has at least 5 labeled
outcomes. Small samples remain visible but descriptive only.

V2.2.3 does not recommend or apply a threshold change. Threshold calibration
is a later explicit stage.

## Outputs

- JSON performance report
- Markdown performance report
- actionable-segment rankings when sufficient samples exist

## Safety

- canonical feature engine modified: FALSE
- Paper selector modified: FALSE
- threshold changes: DISABLED
- broker network: OFF
- Paper orders: 0
- Live orders: 0
- Live trading: LOCKED
