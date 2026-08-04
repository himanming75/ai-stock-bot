# V141-V145 Web Controller Foundation

## Start

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V141_01_TO_V145_64_WEB_CONTROLLER.ps1
```

Open:

`http://127.0.0.1:8765`

## Available controls

- View V140 release state
- View Alpaca Paper account, positions and orders
- View Shadow status and qualification
- View Dynamic Risk state
- View Autonomous Orchestrator state
- View recent ledgers
- Run V140 refresh
- Run offline Shadow
- Run offline Autonomous Cycle
- Emergency Stop ON/OFF

## Safety

The controller binds only to `127.0.0.1`.

The Emergency Stop starts ON.

No Live API action exists.

Actual Live orders remain zero.
