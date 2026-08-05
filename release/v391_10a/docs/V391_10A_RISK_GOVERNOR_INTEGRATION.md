# V391.10A Risk Governor Integration

## Purpose

Integrate V391.01A through V391.09A into one fail-closed Risk Governor decision.

## Final decisions

- `ALLOW`: all required stages are present, PASS, consistent, and non-blocking;
- `WARN`: no blocking condition exists, but at least one warning is active;
- `BLOCKED`: a source is missing, invalid, inconsistent, failed, or blocking.

## Important boundary

`ALLOW` means the Risk Governor permits the next authorization stage to evaluate
the request. It does not itself authorize or submit an order.

Execution Authorization remains disabled until V392.

## Safety

- no broker network;
- no order submission;
- no order cancellation;
- no position changes;
- policy hashes must match;
- missing or failed inputs block by default.
