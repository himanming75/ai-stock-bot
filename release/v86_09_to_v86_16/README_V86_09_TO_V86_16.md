# V86.09-V86.16 Indicator Engine

## Included stages

- V86.09 OHLCV input validation
- V86.10 SMA and EMA calculations
- V86.11 RSI calculation
- V86.12 MACD, signal line, and histogram
- V86.13 ATR and true range
- V86.14 Bollinger Bands and VWAP
- V86.15 Indicator-to-strategy signal conversion
- V86.16 Dashboard integration, test, verify, and one-click release

## Safety

- Local calculations only
- No external network
- No broker credentials
- No broker writes
- No order submission
- No live trading

## Run

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V86_09_TO_V86_16_INDICATOR_ENGINE.ps1
```
