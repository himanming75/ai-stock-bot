# Broker Integration V2.1.6 — Canonical Signal Source Bridge

Base commit: `78424be7`

## Audit result
The repository already contains the canonical V79.71-V79.75 historical signal engine:
`alpaca_market_data/historical_signal_engine_v79_71_75.py`.

That engine already converts indicator rows into BUY / SELL / HOLD using:
- MACD direction
- ROC momentum
- stochastic extremes
- Bollinger-band position
- configured buy/sell thresholds
- a 0..1 confidence field

V2.1.6 therefore does NOT create another strategy engine.

## What V2.1.6 adds
It adapts the existing canonical signal rows into the V2.1.5 recommendation contract:
`symbol/action/confidence/quantity/strategy_id`.

It selects the latest signal per symbol/timeframe, then passes those recommendations through the existing V2.1.5 confidence/HOLD gate.

## Safety boundary
This stage is an OFFLINE source bridge.
It does not fetch new market data over the network.
It does not call E*TRADE order endpoints.
It does not enable PROD or live trading.
It does not claim profitability.

## Next stage
V2.1.7 should connect an approved current/read-only market-data source to the already-existing indicator/signal path, while preserving the same V2.1.5/V2.1.4 execution gates.
