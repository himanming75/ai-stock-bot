# V139.08 Submitted Order Acceptance Verification

This stage validates a local submission-result snapshot against the V139.07 launch result, preparation token, and preview.

Supported initial submission statuses:

- NEW
- ACCEPTED
- PENDING_NEW
- REJECTED

Accepted statuses create a local acceptance token and enable V139.09 lifecycle monitoring.
REJECTED is recorded as a valid rejected result but does not enable lifecycle monitoring.
Missing IDs, mismatched order fields, unsupported statuses, or conflicting tokens enter safe mode.

No broker network request or order submission is performed.
