# Broker Integration V2.1.8.1 — Alpaca REST Bootstrap Diagnostic Repair

Base commit: `80e5d4a5`

## Observed issue
Actual V2.1.8 REST bootstrap returned enough bars for SPY but 0 bars for AAPL and MSFT.

## Repair
Only the existing V2.1.8 Alpaca historical REST adapter is enhanced.

Added:
- HTTP status visibility
- safe response headers capture
- symbol-by-symbol raw bar count
- selected bar count
- first / last timestamp per symbol
- pagination visibility
- pagination support using `next_page_token`
- bounded page loop

## Safety
No broker order endpoint is added.
PROD and live trading remain locked.
