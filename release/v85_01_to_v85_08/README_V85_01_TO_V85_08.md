# V85.01-V85.08 Dashboard v2

## Stages

- V85.01 source discovery
- V85.02 state normalization
- V85.03 safety-boundary aggregation
- V85.04 runtime summary cards
- V85.05 state table and raw JSON view
- V85.06 local JSON API and health endpoint
- V85.07 localhost-only server policy
- V85.08 export, test, verify, and release integration

## Start

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V85_01_TO_V85_08_DASHBOARD_V2.ps1
```

Open:

`http://127.0.0.1:8501`

The page refreshes every 15 seconds.

## Safety

- Read-only
- Localhost only
- No external network
- No credentials
- No broker writes
- No order submission
- No live trading
- No additional Python package required
