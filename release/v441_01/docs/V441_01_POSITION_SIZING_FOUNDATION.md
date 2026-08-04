# V441.01 Position Sizing Foundation

## Scope

This substage calculates recommended notional and quantity using:

- account equity;
- fixed risk budget per position;
- reference price;
- stop-loss distance;
- V430 proposed portfolio weight;
- maximum single-position percentage.

## Formula

```text
risk_budget = account_equity × risk_per_trade_pct
maximum_notional_by_risk = risk_budget ÷ stop_loss_pct
maximum_notional_by_weight = account_equity × min(proposed_weight, maximum_position_pct)
recommended_notional = min(maximum_notional_by_risk, maximum_notional_by_weight)
quantity = recommended_notional ÷ reference_price
```

## Deliberately deferred

- V442: Kelly sizing;
- V443: volatility scaling;
- V444: sector exposure;
- V445: portfolio risk budget;
- V446: drawdown scaling;
- V447: correlation adjustment;
- V448: cash reserve;
- V449: integrated allocation;
- V450.64: qualification and release.

All results are analytical only. No broker client or order submission is present.
