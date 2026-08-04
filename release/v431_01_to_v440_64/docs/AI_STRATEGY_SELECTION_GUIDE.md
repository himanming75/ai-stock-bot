# V431.01–V440.64 AI Strategy Selection Engine

## Purpose

Choose the most suitable offline analytical strategy for the current market regime.

## Strategies

- Trend Following
- Momentum
- Breakout
- Mean Reversion
- Cash Defensive

## Inputs

- market regime;
- trend strength;
- momentum strength;
- breakout strength;
- mean-reversion strength;
- volatility;
- liquidity;
- market breadth;
- V430 portfolio score.

## Outputs

- selected strategy;
- fallback strategy;
- score and confidence for every strategy;
- eligibility status;
- portfolio compatibility;
- detailed reasons.

The selected strategy is analytical only. No broker client is used and no order can be submitted.

## Run

```powershell
& .\RUN_V431_01_TO_V440_64_AI_STRATEGY_SELECTION.ps1
```

## Test and verify

```powershell
& .\RUN_V431_01_TO_V440_64_TEST_AND_VERIFY.ps1
```
