# V391.07A Kill Switch

## Purpose

Provide a fail-closed control that blocks all new risk operations whenever the
Kill Switch is active.

## Rules

- Kill Switch is mandatory;
- active Kill Switch forces risk operations OFF;
- automatic resume is forbidden;
- manual resume is required;
- invalid policy combinations fail closed.

## States

- `KILL_SWITCH_GUARD_STANDBY`
- `KILL_SWITCH_GUARD_BLOCKED`
- `KILL_SWITCH_GUARD_INVALID`

This stage does not submit, cancel, replace, or modify broker orders.
