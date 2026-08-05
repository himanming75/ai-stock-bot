# V391.03A Maximum Drawdown Guard

## Purpose

Track peak equity and evaluate current drawdown against the validated V391.01A policy.

## Formula

```text
peak_equity = max(previous_peak_equity, current_equity)
drawdown_amount = peak_equity - current_equity
drawdown_pct = drawdown_amount / peak_equity
```

## States

- `MAX_DRAWDOWN_GUARD_ACTIVE`: drawdown is below 75% of the limit;
- `MAX_DRAWDOWN_GUARD_WARNING`: drawdown is at least 75% of the limit;
- `MAX_DRAWDOWN_GUARD_PAUSE_REQUIRED`: drawdown is equal to or greater than the limit.

## Default policy

```text
Maximum drawdown: 10%
Warning threshold: 7.5%
```

A breach disables new risk operations and requires manual resume. This stage does not
submit, cancel, replace, or modify any broker order.
