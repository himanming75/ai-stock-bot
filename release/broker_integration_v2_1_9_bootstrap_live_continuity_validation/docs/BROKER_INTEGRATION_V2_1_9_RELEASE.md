# Broker Integration V2.1.9 — Bootstrap → Live Continuity Validation

Base commit: `6fa0d34e`

## Purpose
Validate that the proven V2.1.8.2 historical bootstrap can be continued with V2.1.7.1 live bars without corrupting the time series.

## Reuse
V2.1.9 reuses:
- V2.1.8.2 symbol-scoped Alpaca REST bootstrap
- V2.1.7.1 Alpaca read-only WebSocket collector
- V2.1.7 current-market signal bridge
- existing V79 indicator/signal engines

No market-data engine, indicator engine, signal engine, or order engine is replaced.

## Continuity rules
- merge key: `(symbol, timestamp)`
- live bar replaces bootstrap bar at identical timestamp
- duplicate timestamps are removed
- chronological order is enforced
- retention is bounded per symbol
- signals are recalculated after the merged series is formed

## Safety
- read-only market data only
- no E*TRADE order submission
- no Alpaca trading endpoint
- PROD locked
- live trading locked
- no profitability claim

## Runtime
Bootstrap-only validation can run even when the market is closed.

Optional live continuity validation uses the existing WebSocket collector. If insufficient live bars arrive before timeout, the bootstrap baseline remains valid and the CLI exits without a broker order.

## Next stage
After actual continuity validation, V2.1.10 can connect only eligible BUY/SELL signals to the already-proven E*TRADE Sandbox bounded controller. PROD/live must remain locked.
