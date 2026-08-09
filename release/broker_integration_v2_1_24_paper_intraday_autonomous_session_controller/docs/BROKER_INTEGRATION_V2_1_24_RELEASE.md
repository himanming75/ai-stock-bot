# V2.1.24 — Paper Intraday Autonomous Session Controller

Base commit: `7ec5c48c`.

## Purpose

Orchestrate the already-built Broker Integration chain without introducing another market-data, signal, broker, order, or exit-strategy engine.

Existing stages reused:

1. V2.1.21 — actual intraday canonical validation
2. V2.1.22 — bounded Alpaca Paper entry bridge
3. V2.1.23 — read-only order/position lifecycle bridge

## Session behavior

`DRY` mode is the default and never submits a broker order.

`PAPER` mode requires:
- explicit `RUN_ALPACA_PAPER_SESSION` session confirmation
- existing V2.1.22 `SUBMIT_ALPACA_PAPER_ONCE` guard internally
- the existing `PAPER_ONLY` arm-token preflight
- Alpaca Paper endpoint
- current V2.1.21 canonical READY evidence

The controller permits at most **one Alpaca Paper entry order per session**.

After a Paper entry, V2.1.23 performs read-only lifecycle monitoring. Automatic exit-order submission remains disabled.

## Stop / no-order behavior

The controller does not submit an order when:
- outside the market session
- bars are stale/invalid
- there is no eligible signal
- canonical provenance is blocked
- current canonical qualification is not READY
- Paper preflight fails
- evidence was already consumed
- an open position already exists
- session Paper order limit was reached

## Safety

Installation/tests:
- broker network: OFF
- Paper orders: 0
- live orders: 0

Actual Paper mode:
- Alpaca Paper only
- maximum one Paper entry/session
- maximum per-order notional remains controlled by V2.1.22 profile ($25 validation profile)
- exit write: OFF
- E*TRADE write: OFF
- live trading: OFF

## Next stage

V2.1.25 will focus on Paper exit execution and restart/recovery guards before a fully unattended multi-trade session is enabled.
