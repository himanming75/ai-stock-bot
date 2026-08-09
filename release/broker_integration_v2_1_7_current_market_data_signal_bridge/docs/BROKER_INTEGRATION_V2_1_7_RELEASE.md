# Broker Integration V2.1.7 — Current Read-Only Market Data Signal Bridge

Base commit: `eaa6ebfe`

## Reuse audit

The repository already contains a real-time Alpaca market-data foundation from V102.01-V103.00:
- `market_data_engine.models.Bar`
- `AlpacaMessageParser`
- `SubscriptionRegistry`
- freshness / sequence / routing infrastructure
- an optional read-only Alpaca websocket runner

The repository also already contains:
- V79.66-V79.70 historical indicator library
- V79.71-V79.75 historical signal engine
- V2.1.6 canonical signal source bridge
- V2.1.5 BUY/SELL/HOLD decision gate

V2.1.7 does not create replacements for any of those engines.

## Added

V2.1.7 connects:
`market_data_engine.Bar`
→ V79 indicator rows
→ V79 BUY/SELL/HOLD signal rows
→ V2.1.6 recommendations
→ V2.1.5 decision queue

A bounded current-bar window is included so only recent bars are retained.

## Actual read-only runner

`START_ALPACA_CURRENT_SIGNAL_SOURCE_V2_1_7.ps1`

The runner:
- requires existing Alpaca market-data credentials
- uses the existing Alpaca IEX read-only websocket source
- subscribes only to bars
- collects a bounded number of bars
- creates recommendations
- submits zero broker orders

## Safety

This stage does NOT connect recommendations to E*TRADE order submission.
PROD remains locked.
Live trading remains locked.
Profitability is not validated.

## Next stage

V2.1.8 should connect only eligible V2.1.5 signals to the already-proven V2.1.4 E*TRADE Sandbox bounded controller, while keeping E*TRADE PROD/live locked.
