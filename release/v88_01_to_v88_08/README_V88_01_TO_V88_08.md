# V88.01-V88.08 Web UI v2

## Included stages

- V88.01 localhost web application shell
- V88.02 backtest result summary cards
- V88.03 local backtest execution form
- V88.04 equity and portfolio curve rendering
- V88.05 trade log table
- V88.06 risk and explainability display
- V88.07 JSON result downloads and health endpoint
- V88.08 test, verify, release, and one-click installation

## Start

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V88_01_TO_V88_08_WEB_UI_V2.ps1
```

Open:

`http://127.0.0.1:8601`

## Safety

- Localhost only
- Historical/paper functions only
- No external network
- No broker credentials
- No broker writes
- No order submission
- No live trading
