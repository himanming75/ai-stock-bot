# AI Trading Engine V2.2.7 — Challenger Shadow Execution Simulator

Base commit: `c3a66a60`.

## Purpose

Create counterfactual outcomes for V2.2.5 `CHALLENGER_ONLY` signals without
submitting any broker order.

## Price path

V2.2.7 reuses the historical V2.2.1 feature snapshot ledger.

For each symbol, the canonical `1m` timeframe feature `close` from successive
snapshots becomes the local shadow price path.

No additional market-data API call is made by V2.2.7.

## Entry

For a `CHALLENGER_ONLY` BUY/SELL signal:
- same symbol;
- signal snapshot/time is preserved;
- first available same-or-later 1m snapshot close becomes the shadow entry;
- quantity is fixed to 1 simulation unit.

This quantity has no relationship to actual account sizing.

## Exit

V2.2.7 reuses the existing:
`paper_position_lifecycle.rules.evaluate_exit`

Therefore stop loss, take profit, trailing stop and configured position policy
remain aligned with the existing Paper lifecycle logic.

A local one-hour shadow maximum is also used so a simulation cannot remain
open indefinitely when enough snapshots are collected.

## Short simulation

The existing exit evaluator is long-oriented. SELL price paths are transformed
into an equivalent return-space mark solely for exit-rule evaluation. Reported
P&L and return are calculated using true short direction.

## Important limitations

Counterfactual results are simulations, not broker fills.

They currently:
- use snapshot 1m close rather than bid/ask execution price;
- do not include spread;
- do not include slippage;
- do not include fees;
- do not claim actual fill probability.

These limitations remain explicit in every completed shadow record.

## Outputs

- open shadow position ledger
- completed shadow round-trip ledger
- latest simulation record
- summary JSON
- refresh-and-simulate PowerShell helper

## Safety

- broker network from V2.2.7: OFF
- actual Paper orders: 0
- Live orders: 0
- Challenger execution at broker: DISABLED
- automatic promotion: DISABLED
- Live trading: LOCKED
