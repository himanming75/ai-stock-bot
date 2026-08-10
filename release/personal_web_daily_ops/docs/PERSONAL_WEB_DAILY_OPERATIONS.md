# Personal Web Control Center — Daily Operations

Reuses the existing Operations Manager and API.

Adds one operational panel for:
- health check;
- pre-market check;
- intraday shadow run;
- post-market report;
- recovery plan;
- schedule settings;
- health/recovery/last-job/notification visibility.

Safety is inherited from the existing backend:
- intraday shadow is read/shadow only;
- scheduled Paper order submission remains disabled;
- live submission remains disabled;
- duplicate scheduled jobs are blocked by the existing job lock;
- pre-market and intraday-shadow jobs are blocked while Emergency Stop is enabled.
