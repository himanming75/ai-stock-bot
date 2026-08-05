# V391.08A Auto Pause

## Purpose

Aggregate the outputs of all Risk Governor guards and move the system to a
fail-closed paused state when any blocking or invalid condition is detected.

## Inputs

- Daily Loss Guard
- Maximum Drawdown Guard
- Position Size Guard
- Total Exposure Guard
- Symbol Concentration Guard
- Kill Switch Guard

## States

- `AUTO_PAUSE_GUARD_STANDBY`
- `AUTO_PAUSE_GUARD_WARNING`
- `AUTO_PAUSE_GUARD_PAUSED`

## Rules

- any blocking guard state pauses new risk;
- any guard with `status != PASS` pauses new risk;
- any guard with `risk_operations_allowed = false` pauses new risk;
- automatic resume is disabled;
- manual resume is required after a pause.

This stage does not submit, cancel, replace, or modify broker orders.
