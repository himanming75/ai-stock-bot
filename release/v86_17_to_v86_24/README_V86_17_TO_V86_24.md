# V86.17-V86.24 Portfolio Scoring Engine

## Included stages

- V86.17 multi-symbol candidate model
- V86.18 decision and confidence scoring
- V86.19 volatility risk adjustment
- V86.20 liquidity adjustment and ranking
- V86.21 per-symbol position cap
- V86.22 sector exposure cap
- V86.23 portfolio allocation and diversification score
- V86.24 Dashboard integration, test, verify, and one-click release

## Safety

- Local ranking and allocation only
- No external network
- No broker credentials
- No broker writes
- No order submission
- No live trading

## Run

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V86_17_TO_V86_24_PORTFOLIO_SCORING.ps1
```
