# V2.1.31 — One-Click Daily Alpaca Paper Operation

Base commit: `2a6155b4`.

## Scope

V2.1.31 is an operations launcher only.

It does not create a new:
- market-data engine
- signal engine
- entry engine
- lifecycle engine
- exit engine
- risk engine
- recovery engine
- trading state machine

The operational chain remains:

V2.1.30 recovery supervisor
→ V2.1.29 daily risk guard
→ V2.1.28 bounded continuous Paper session
→ V2.1.26/V2.1.27 existing round-trip execution and reconciliation

## New responsibilities

V2.1.31 adds only:

1. one daily user-facing start point;
2. startup recovery reconciliation before waiting;
3. pre-risk check before waiting;
4. Paper read-only market-open wait;
5. delegation to V2.1.30 once the market is open;
6. compact end-of-operation summary.

## Market wait

Initial policy:
- polling interval: 60 seconds
- maximum wait: 64,800 seconds (18 hours)
- maximum round-trips: 2
- delegated session interval: 30 seconds

Waiting uses only the existing Paper read path through V2.1.30. No order method is invoked while the market is closed.

If broker reads fail beyond the existing recovery retry policy, the daily operation stops rather than trading blind.

## Dry plan

`START_V2_1_31_DAILY_OPERATION_DRY_PLAN.ps1`

uses no broker network and no orders. It checks only:
- local recovery plan
- current V2.1.29 risk permission
- whether the real Paper launcher would be allowed to proceed.

## Paper launcher

`START_V2_1_31_ONE_CLICK_ALPACA_PAPER_DAY.ps1`

requires the exact confirmation:

`RUN_ONE_CLICK_DAILY_ALPACA_PAPER_OPERATION`

and verifies the Alpaca Paper endpoint before starting.

## Safety

Install/tests:
- broker network: OFF
- Paper orders: 0
- Live orders: 0

Live trading remains locked.

## Completion boundary

V2.1.31 completes the one-command daily Paper operating path.

V2.1.32 is reserved for daily performance/operations reporting and does not add another execution engine.
