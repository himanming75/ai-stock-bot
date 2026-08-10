# AI Trading Engine V2.2.9 — Training Dataset Builder

Base commit: `5b5777a6`.

## Purpose

Convert the V2.2.8.1 forward-labeled minute dataset into leakage-controlled
machine-learning matrices.

V2.2.9 is local/offline only. It uses no Alpaca network endpoint and submits no order.

## Source

`runtime/ai_fast_data_acceleration_v2_2_8/training_forward_labels.jsonl`

If the V2.2.8.1 historical backfill is still running or the source does not yet exist,
installation/tests remain valid and the actual V2.2.9 build reports WAITING.

## Streaming architecture

The expected source can contain hundreds of thousands of rows.

V2.2.9 uses two passes instead of loading the full JSONL into memory:

1. scan unique market dates and source counts;
2. stream rows into final CSV matrices.

## Features

- return_1m_pct
- return_5m_pct
- return_15m_pct
- close_vs_sma20_pct
- rolling_volatility_20
- volume_ratio_20
- range_pct
- rsi_14

Absolute future price/return fields are never feature inputs.

## Targets

Separate matrices are built for 5, 15, 30 and 60-minute horizons.

Each contains:

- target forward return
- MFE
- MAE
- UP / DOWN / FLAT direction
- target timestamp

Direction uses a 0.05% deadband by default.

## Leakage control

Rows are split by market date, never randomly.

Chronological layout:

TRAIN
→ one trading-day embargo
→ VALIDATION
→ one trading-day embargo
→ TEST

The builder verifies chronological ordering before marking a dataset ready.

Default usable-date allocation is 70% / 15% / 15%.

## Outputs

`runtime/ai_training_dataset_builder_v2_2_9/datasets/`

- train_5m.csv / validation_5m.csv / test_5m.csv
- train_15m.csv / validation_15m.csv / test_15m.csv
- train_30m.csv / validation_30m.csv / test_30m.csv
- train_60m.csv / validation_60m.csv / test_60m.csv

`dataset_manifest.json` records:

- source SHA-256
- row counts
- split dates
- class balance
- output SHA-256
- skipped-row reasons
- leakage guard results

## Safety

- Broker network: OFF
- Order submission: 0
- V2.1.31 execution selector modified: FALSE
- Automatic promotion: DISABLED
- Live trading: LOCKED
