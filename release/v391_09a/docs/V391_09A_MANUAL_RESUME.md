# V391.09A Manual Resume

## Purpose

Allow a paused Risk Governor to return to monitoring only after explicit,
time-limited, manual approval and confirmation that blocking conditions have
cleared.

## Required conditions

- V391.08A pause condition is cleared;
- Kill Switch is inactive;
- approval phrase exactly matches `APPROVE_MANUAL_RISK_RESUME`;
- operator identity and reason are present;
- approval request has not expired;
- automatic resume remains disabled.

## States

- `MANUAL_RESUME_GUARD_APPROVED`
- `MANUAL_RESUME_GUARD_BLOCKED`

Approval only changes the internal risk-monitoring state. It does not submit,
cancel, replace, or modify broker orders.
