# Validation Auto Scheduler + Daily History

Adds only two capabilities:
1. A local background supervisor that triggers the existing Validation Lab
   full-refresh action at configured weekday times.
2. Date-based validation snapshots and recent history.

Default local PC times:
- 07:30
- 13:20

The background supervisor continues independently of the 8767 web process
after it has been started. It stops when a STOP file is requested.

History stores factual values only:
- observed validation days;
- resolved outcomes;
- waiting future marks;
- AI health;
- research readiness;
- Paper qualification;
- blockers and next milestone.

Safety:
- no E*TRADE usage;
- no broker network;
- Paper engine is not started;
- no Paper/Live order submission;
- no synthetic trading days;
- no fabricated future outcomes.

The PC must be powered on for scheduled refreshes to occur.
