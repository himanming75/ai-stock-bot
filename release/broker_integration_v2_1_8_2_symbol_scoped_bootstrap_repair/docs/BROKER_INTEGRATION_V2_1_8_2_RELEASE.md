# Broker Integration V2.1.8.2 — Symbol-Scoped Bootstrap Repair

Base commit: `524cb7f7`

## Actual evidence
The V2.1.8.1 diagnostic run showed:
- HTTP 200
- IEX feed
- 20 pages consumed
- a next page token still remained
- AAPL returned 0 rows
- MSFT and SPY returned thousands of rows

This means the REST transport and credentials were working, but the multi-symbol paginated request was not a reliable bootstrap method for obtaining a small recent sample for every requested symbol.

## Repair
The same Alpaca read-only REST endpoint is retained, but bootstrap is now requested one symbol at a time.

Each symbol:
- has its own pagination state
- stops immediately after enough bars are collected
- is independently diagnosed
- remains bounded to 20 pages

This avoids one symbol's pagination ordering from starving another requested symbol.

## Safety
No broker trading endpoint is added.
Broker order submission remains disabled.
PROD and live trading remain locked.
