# V391.05A Total Exposure Guard

## Purpose

Prevent gross portfolio exposure from exceeding the validated total exposure
limit after a proposed order is added.

## Formula

```text
current_exposure = sum(abs(position.market_value))
projected_exposure = current_exposure + proposed_order_notional
projected_exposure_pct = projected_exposure / equity
```

## Default policy

```text
Maximum total exposure: 50% of equity
Warning threshold: 80% of the total exposure limit
```

## States

- `TOTAL_EXPOSURE_GUARD_ACTIVE`
- `TOTAL_EXPOSURE_GUARD_WARNING`
- `TOTAL_EXPOSURE_GUARD_BLOCKED`

Long and short market values are counted by absolute value. The guard calculates
an allowed notional but does not automatically resize, submit, cancel, or modify
orders.
