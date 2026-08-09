# V2.1.25.1 — Empty Position Fixture Repair

Base HEAD remains `d29a37be` because V2.1.25 failed before commit/push.

## Root cause

The V2.1.25 production recovery logic correctly checks:

`if symbol not in open_symbols`

to prevent a duplicate exit after restart when the Paper position is already closed.

The synthetic fixture incorrectly initialized the fake open-position set with:

`set(open_symbols or {"AAPL"})`

An explicitly supplied empty set is falsy in Python, so the fixture replaced it
with `{"AAPL"}`. The recovery test therefore simulated an open position instead
of an already-closed position.

## Repair

Only the synthetic test fixture is changed.

`None` now means "use default AAPL", while an explicitly supplied empty set
remains empty.

The production V2.1.25 exit/recovery logic is unchanged.

## Safety

- installation tests use no broker network
- Paper exit orders during tests: 0 actual broker orders
- live orders: 0
- live trading remains locked
