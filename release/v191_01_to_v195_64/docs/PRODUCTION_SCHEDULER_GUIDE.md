# V191-V195 Production Scheduler Automation

Safe scheduled jobs:

- Pre-market V140 readiness
- Market-open health check
- Qualification recalculation
- Portfolio refresh
- Post-market report generation
- Nightly backup

Safety:

- all schedules disabled by default
- duplicate execution lock
- retry support
- Task Scheduler `IgnoreNew`
- no Paper order submission
- no Live order submission
- no broker write

Enable the desired jobs in the policy JSON, then run the installer as Administrator.
