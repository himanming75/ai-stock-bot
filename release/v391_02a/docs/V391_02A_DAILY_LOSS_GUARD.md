# V391.02A Daily Loss Guard

## Purpose

Evaluate current-day loss against the validated V391.01A policy.

## Formula

```text
daily_pnl = equity - last_equity
daily_return_pct = daily_pnl / last_equity
daily_loss_pct = max(0, -daily_return_pct)
```

## States

- `DAILY_LOSS_GUARD_ACTIVE`: loss is below 75% of the limit;
- `DAILY_LOSS_GUARD_WARNING`: loss is at least 75% of the limit;
- `DAILY_LOSS_GUARD_PAUSE_REQUIRED`: loss is equal to or greater than the limit.

## Default policy

```text
Daily loss limit: 2%
Warning threshold: 1.5%
```

A breach disables new risk operations and requires manual resume. This stage does not
submit, cancel, replace, or modify any broker order.
