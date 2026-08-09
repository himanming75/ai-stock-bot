# Broker Integration V2.1.14 — Market Session Awareness + Freshness Guard

Base commit: `c946e786`

## Purpose

Prevent V2.1.13-style observation from treating an old completed bar as if it were a current live market state.

## Design

This stage deliberately does **not** create a holiday calendar or claim the exchange is open based on clock time alone.

It classifies only:
- weekday vs weekend
- whether current New York time is inside the regular 09:30–16:00 clock window

Then it independently validates bar freshness.

Signal capture is allowed only when:
1. current time is inside the regular clock window, and
2. all required symbols have sufficiently fresh timestamps.

## Default freshness

- maximum bar age: 180 seconds
- maximum future skew: 10 seconds

## Reuse

V2.1.14 reuses:
- V2.1.12 end-to-end plan
- V2.1.8.2 bootstrap diagnostics
- their already-collected latest bar timestamps

It performs no duplicate market-data fetch.

## Blocking behavior

Outside regular window:
`WAITING_OUTSIDE_REGULAR_WINDOW`

Inside regular window with stale/missing/future timestamps:
`BLOCK_STALE_OR_INVALID_BAR`

Only fresh bars inside the regular window:
`PASS_REGULAR_WINDOW_FRESH_BARS`

## Safety

V2.1.14:
- never starts E*TRADE OAuth
- never sends Sandbox Preview
- never sends Sandbox Place
- submits zero broker orders
- keeps PROD locked
- keeps live trading locked
- makes no profitability claim
