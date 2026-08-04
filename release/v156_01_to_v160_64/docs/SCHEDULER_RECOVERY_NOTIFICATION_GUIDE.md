# V156-V160 Scheduler, Recovery & Notifications

## Safe defaults

All schedules are disabled by default.

Scheduled order submission is unavailable.

Live submission is disabled.

## Supported jobs

- Web controller at Windows logon
- Pre-market V140 readiness check
- Intraday real Alpaca Paper Shadow read
- Post-market health and report
- Health check
- Recovery-plan generation

The intraday scheduled job is Shadow/read-only and does not submit an order.

## Install selected tasks

First save settings in the `Scheduler & Recovery` web tab.

Then run PowerShell as Administrator:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\release\v156_01_to_v160_64\scheduler\INSTALL_SAFE_SCHEDULED_TASKS.ps1
```

## Remove tasks

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\release\v156_01_to_v160_64\scheduler\REMOVE_SAFE_SCHEDULED_TASKS.ps1
```
