# V87.01-V87.08 Backtest Engine V2

## Included stages

- V87.01 historical OHLCV replay
- V87.02 local virtual broker fills
- V87.03 commission and slippage accounting
- V87.04 realized PnL and total return
- V87.05 trade statistics
- V87.06 risk statistics and drawdown curve
- V87.07 equity curve, trade log, and Dashboard integration
- V87.08 test, verify, release, and one-click installation

## Safety

- Historical replay only
- No external network
- No broker credentials
- No broker writes
- No order submission
- No live trading

## Run

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V87_01_TO_V87_08_BACKTEST_V2.ps1
```
