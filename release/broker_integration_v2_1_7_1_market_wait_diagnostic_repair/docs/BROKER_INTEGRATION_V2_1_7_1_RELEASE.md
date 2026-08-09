# Broker Integration V2.1.7.1 — Market Wait Diagnostic Repair

Base commit: `1d53991f`

## Problem observed
The actual V2.1.7 Alpaca current-data test entered the WebSocket collector and appeared to stop because no progress or connection-state information was printed while waiting for bars.

## Repair
Only the existing V2.1.7 current-bar collector is enhanced.

Added:
- WebSocket CONNECTED message
- Alpaca authentication PASS message
- subscription PASS message
- per-symbol progress such as `AAPL 1/3 | MSFT 0/3 | SPY 0/3`
- periodic waiting messages
- raw-message and parsed-bar counts
- explicit timeout diagnostic
- conservative explanation that the market *may* be closed or the selected feed may currently be idle

## Important
This repair does not assert that the market is closed based only on a lack of bars.

## No duplication
The V2.1.7 market-data/indicator/signal pipeline is unchanged.
Only `alpaca_readonly_current_bar_collector_v2_1_7.py` is repaired.

## Safety
- Read-only market data only
- Broker order submission: OFF
- PROD: LOCKED
- Live trading: LOCKED
