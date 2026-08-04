# V266-V270 Windows Autostart & Recovery

Features:

- Windows Task Scheduler registration scripts
- Supervisor process
- Restart on child-process failure
- Maximum restart limit and backoff
- Stale session-lock inspection and cleanup
- Last checkpoint recovery plan
- Stop-file awareness
- Paper account/order/position reconciliation plan
- Log retention cleanup
- Web API foundation

Safety defaults:

- Task is not registered automatically
- Autostart registration disabled
- Supervisor disabled
- Child execution disabled in verification
- Live submission/network/write remain disabled

Registering the Windows task requires an explicit script and confirmation phrase.
