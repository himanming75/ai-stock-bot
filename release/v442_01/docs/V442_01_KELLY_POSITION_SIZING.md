# V442.01 Kelly Position Sizing

## Purpose

Apply a conservative fractional-Kelly limit on top of the V441 fixed-risk position size.

## Formula

```text
b = average_win / average_loss
full_kelly = win_rate - ((1 - win_rate) / b)
fractional_kelly = max(0, full_kelly) × kelly_fraction
capped_kelly = min(fractional_kelly, maximum_kelly_pct)
kelly_notional_limit = account_equity × capped_kelly
final_notional = min(V441_notional, kelly_notional_limit)
```

## Safety

- negative Kelly edge produces zero Kelly allocation;
- fractional Kelly defaults to 50%;
- maximum Kelly allocation defaults to 20%;
- no broker network;
- no order creation or submission.

## Next stage

V443.01 will add volatility scaling independently.
