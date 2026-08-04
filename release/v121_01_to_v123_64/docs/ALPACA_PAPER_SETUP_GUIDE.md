# Alpaca Paper Setup Guide — FIXED V2

No JSON policy edit is required.

## Set Paper credentials for the current PowerShell window

```powershell
$env:ALPACA_PAPER_API_KEY="YOUR_NEW_PAPER_KEY"
$env:ALPACA_PAPER_SECRET_KEY="YOUR_NEW_PAPER_SECRET"
```

## Check setup

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\CHECK_V121_ALPACA_PAPER_SETUP.ps1
```

## Real Alpaca Paper read-only connection

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V121_TO_V123_REAL_READ_ONLY.ps1
```

The script temporarily enables the Paper network only for that process. It does not modify the policy JSON.

## Submit one Paper order

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V121_TO_V123_SUBMIT_ONE_PAPER_ORDER.ps1
```

Type `PAPER` at the confirmation prompt.

The script temporarily enables one Paper order and restores the environment afterward.

The Live trading domain and Live order submission remain disabled.
