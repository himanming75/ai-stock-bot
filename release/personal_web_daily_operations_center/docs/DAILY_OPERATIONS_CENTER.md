# Daily Operations Center

Adds a coordination layer to the existing Personal Control Center.

Shows:
- 8770 Control Center status;
- Validation day/sample progress;
- AI health and Final Qualification decision;
- Validation Scheduler status/PID;
- safety/integrity checks;
- today's required action;
- latest saved operations snapshot.

Actions:
- Run Daily Check;
- Save Operations Snapshot;
- Start Validation Scheduler;
- Stop Validation Scheduler.

It intentionally does NOT:
- start the Paper trading engine;
- submit Paper or Live orders;
- connect to E*TRADE;
- change strategy, threshold, model, or risk;
- restart the 8770 process from inside itself.

This keeps process lifecycle separate from the web server.
