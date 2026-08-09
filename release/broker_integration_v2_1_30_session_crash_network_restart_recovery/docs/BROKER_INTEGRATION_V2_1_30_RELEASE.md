# V2.1.30 — Session Crash / Network / Restart Recovery

Base commit: `a6f487c4`.

## Scope

V2.1.30 is a recovery supervisor only. It does not create a new trading state machine, signal engine, entry engine, exit engine, or risk engine.

It reuses:
- V2.1.26 recovery-first current-cycle state
- V2.1.27 final exit-fill reconciliation
- V2.1.28 completed-cycle safe rollover
- V2.1.29 daily risk budget and kill switch
- existing `AlpacaPaperReadClient` for Paper-only broker reads

## Startup recovery

On restart the supervisor:

1. reads the durable V2.1.26 state;
2. obtains an Alpaca Paper broker snapshot with bounded retries;
3. compares local entry/exit/position expectations against broker order and position state;
4. classifies the next safe action:
   - IDLE_START
   - RESUME_V2_1_26_RECOVERY_FIRST
   - RUN_V2_1_27_FINAL_RECONCILIATION
   - RUN_V2_1_28_SAFE_ROLLOVER
   - FAIL_CLOSED
5. delegates actual continued operation back to V2.1.29 only after successful recovery reconciliation.

## Network policy

Initial policy:
- broker read attempts: 3
- retry delay: 2 seconds
- retries exhausted: fail closed
- no recovery-time broker write

## Mismatch policy

Examples that fail closed:
- broker position exists with no active local cycle
- entry order expected locally but absent at broker
- filled entry but expected position is absent
- filled exit but position still remains
- completed local cycle lacks V2.1.28 rollover proof

In Paper mode a failed recovery reuses the existing V2.1.29 kill switch.

## Safety

Installation and unit tests:
- broker network: OFF
- Paper orders: 0
- Live orders: 0

Read-only recovery reconciliation:
- Paper broker reads: allowed
- broker writes: 0

Live trading remains locked.

## Next

V2.1.31 — One-Click Daily Paper Operation.
