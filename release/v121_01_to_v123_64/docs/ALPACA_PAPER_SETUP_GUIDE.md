# Alpaca Paper Setup Guide

## Safety defaults

The installed policy starts with:

- `real_network_enabled: false`
- `paper_submission_enabled: false`
- `live_submission_enabled: false`

Offline validation runs without credentials.

## Environment variables

Use Paper credentials only:

```powershell
$env:ALPACA_PAPER_API_KEY="YOUR_PAPER_KEY"
$env:ALPACA_PAPER_SECRET_KEY="YOUR_PAPER_SECRET"
```

Never commit keys to Git.

## Enable real read-only Paper connection

Edit:

`release/v121_01_to_v123_64/input/alpaca_paper_policy.json`

Set:

```json
"real_network_enabled": true
```

Then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V121_TO_V123_REAL_READ_ONLY.ps1
```

## Enable one Paper order

Only after verifying the account is the Alpaca Paper account, also set:

```json
"paper_submission_enabled": true
```

Then run the explicit order command:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V121_TO_V123_SUBMIT_ONE_PAPER_ORDER.ps1
```

This submits the configured sample order to Alpaca Paper only. The Live API domain is not used.
