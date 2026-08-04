# V443.01 Volatility Scaling Engine

## Purpose

Scale the V442 Kelly-adjusted position size using target volatility.

## Formula

```text
volatility_multiplier = target_volatility / observed_volatility
bounded_multiplier = clamp(
    volatility_multiplier,
    minimum_volatility_multiplier,
    maximum_volatility_multiplier
)
final_notional = V442_notional × bounded_multiplier
```

The default maximum multiplier is 1.0, so this stage may reduce or preserve a position,
but cannot increase it above the V442 result.

## Safety

- no broker network;
- no credential use;
- no order creation or submission;
- Paper and Live orders remain zero.

## Next stage

V444.01 will add sector-exposure limits independently.
