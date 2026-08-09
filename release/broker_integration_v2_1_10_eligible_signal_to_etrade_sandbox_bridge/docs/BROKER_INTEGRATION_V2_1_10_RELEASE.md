# Broker Integration V2.1.10 — Eligible Signal → E*TRADE Sandbox Bridge

Base commit: `987495b6`

## Purpose
Connect only already-eligible V2.1.5/V2.1.9 BUY/SELL signals to the proven V2.1.4 E*TRADE Sandbox bounded controller.

## Reuse
The existing V2.1.5 decision queue already exposes only `order_eligible` signals as `SandboxCycleSignal` objects. The existing V2.1.4 controller already enforces:
- max 3 cycles
- cooldown
- duplicate-signal guard
- kill switch
- stop on error
- Sandbox-only status

V2.1.10 adds only a thin bridge between those two existing contracts.

## Zero-order rule
If `eligible_signal_count == 0`, V2.1.10 returns:
`PASS_NO_ELIGIBLE_SIGNALS_NO_ORDER`

In that case:
- E*TRADE OAuth is not started
- no Preview occurs
- no Place occurs
- no broker order is submitted

## Actual Sandbox runtime
`START_V2_1_10_ELIGIBLE_SIGNAL_TO_ETRADE_SANDBOX.ps1`

Flow:
Alpaca read-only historical bootstrap
→ existing indicator/signal engine
→ V2.1.5 eligible queue
→ explicit `RUN_ELIGIBLE_SANDBOX` confirmation
→ E*TRADE Sandbox OAuth
→ account selection
→ V2.1.4 bounded controller

## Safety
PROD is not enabled.
Live trading is not enabled.
Profitability is not validated.
