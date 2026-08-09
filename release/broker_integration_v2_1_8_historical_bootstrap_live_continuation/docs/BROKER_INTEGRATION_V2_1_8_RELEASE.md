# Broker Integration V2.1.8 — Historical Bootstrap + Live Continuation

Base commit: `ec7a75d6`

## Purpose
Avoid indefinite waiting when the market is closed or the live feed is idle.

V2.1.8 first retrieves recent completed 1-minute bars from the Alpaca read-only market-data REST endpoint, creates indicator/signal results through the already-existing V79/V2.1.7 path, and can optionally continue with the already-existing V2.1.7 WebSocket collector.

## Reuse
- `market_data_engine.Bar`
- V79.66-V79.70 indicator engine
- V79.71-V79.75 signal engine
- V2.1.6 canonical signal bridge
- V2.1.7 current market-data signal bridge
- V2.1.7.1 diagnostic WebSocket collector

The existing V79 incremental sync layer remains untouched. It is an offline merge/checkpoint/gap-fill layer, not the REST transport.

## Added
One read-only Alpaca REST adapter for recent completed bars plus an orchestrator for:
`historical bootstrap -> signal -> optional live continuation`.

## Safety
- Alpaca market-data credentials only
- no Alpaca trading endpoint
- no E*TRADE order endpoint
- broker orders submitted: 0
- PROD locked
- live trading locked
- no profitability claim
