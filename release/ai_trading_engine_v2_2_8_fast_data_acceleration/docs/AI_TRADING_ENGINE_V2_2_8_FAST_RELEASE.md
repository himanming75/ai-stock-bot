# AI Trading Engine V2.2.8 — FAST DATA ACCELERATION

Base commit: `73c9b9c3`.

## Goal

Accelerate AI validation and dataset growth without increasing Paper trading risk.

This stage is market-data-only and does not alter V2.1.31 Paper execution.

## A. Historical backfill

Default:

- 30 liquid US stocks/ETFs
- Alpaca historical stock bars
- 1 minute
- IEX feed
- 90 calendar-day lookback (roughly ~60 trading sessions depending on calendar)
- end time kept 20 minutes behind current time
- pagination up to 10,000 bars/page
- retries for rate-limit/server errors

Outputs:

- `historical_1m_bars.jsonl`
- deterministic per-symbol counts and SHA-256 state

## B. Forward-label dataset

Every historical minute receives locally calculated model inputs where available:

- 1m / 5m / 15m backward return
- SMA 5 / SMA 20
- close-vs-SMA20
- rolling 20-minute volatility
- 20-minute volume ratio
- minute range percent
- RSI 14

Forward labels:

- +5 minute return / MFE / MAE
- +15 minute return / MFE / MAE
- +30 minute return / MFE / MAE
- +60 minute return / MFE / MAE

Exact future timestamps are required. Labels do not bridge overnight/session gaps.

This dataset is for model research/training and is not a claim of executable fills.

## C. 30-symbol live shadow collector

One market-data request per minute retrieves latest IEX minute bars for the 30-symbol universe.

AAPL/MSFT/SPY remain the existing Paper trading universe.
The other 27 symbols are data-only and cannot submit orders.

## Safety boundary

- trading/broker endpoint: NOT USED
- order submission: DISABLED
- actual Paper universe modified: FALSE
- V2.1.31 selector modified: FALSE
- Live trading: LOCKED

## Important interpretation

Historical/shadow labels accelerate model development and validation but do not replace
real Paper fill validation. IEX is not the full consolidated US market feed.

## Commands

Historical backfill:

`powershell -ExecutionPolicy Bypass -File .\START_V2_2_8_FAST_HISTORICAL_BACKFILL.ps1`

Live collector:

`powershell -ExecutionPolicy Bypass -File .\START_V2_2_8_LIVE_30_SYMBOL_SHADOW_COLLECTOR.ps1`

Stop live collector:

`powershell -ExecutionPolicy Bypass -File .\STOP_V2_2_8_LIVE_30_SYMBOL_SHADOW_COLLECTOR.ps1`
