# V391.04A Position Size Limit

## Purpose

Prevent a single position from exceeding the validated maximum position
percentage after a proposed order is added.

## Formula

```text
maximum_position_value = equity × maximum_position_pct
projected_position_value = current_position_value + proposed_order_notional
projected_position_pct = projected_position_value ÷ equity
```

## Default policy

```text
Maximum position: 10% of equity
Warning threshold: 80% of the position limit
```

## States

- `POSITION_SIZE_GUARD_ACTIVE`
- `POSITION_SIZE_GUARD_WARNING`
- `POSITION_SIZE_GUARD_BLOCKED`

The guard calculates an allowed notional but does not automatically resize,
submit, cancel, or modify orders.
