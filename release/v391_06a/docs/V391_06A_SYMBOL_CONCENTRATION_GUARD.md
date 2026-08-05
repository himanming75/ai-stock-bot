# V391.06A Symbol Concentration Guard

## Purpose

Prevent a single symbol from exceeding the validated symbol-exposure limit
after a proposed order is added.

## Formula

```text
current_symbol_value = sum(abs(position.market_value) for matching symbol)
projected_symbol_value = current_symbol_value + proposed_order_notional
projected_symbol_exposure_pct = projected_symbol_value / equity
```

## Default policy

```text
Maximum symbol exposure: 10% of equity
Warning threshold: 80% of the symbol limit
```

## States

- `SYMBOL_CONCENTRATION_GUARD_ACTIVE`
- `SYMBOL_CONCENTRATION_GUARD_WARNING`
- `SYMBOL_CONCENTRATION_GUARD_BLOCKED`

The guard calculates allowed notional but does not automatically resize,
submit, cancel, or modify orders.
