# Validation Auto Scheduler / History Backend Repair

Problem repaired:
- UI was updated, but `/api/validation-lab` did not return `scheduler` or `history`.
- `start_auto_scheduler` returned `ACTION_NOT_ALLOWED`.

This package replaces only:
- `web_controller/validation_lab_api.py`
- `validation_automation/__init__.py`
- `validation_automation/scheduler.py`

It does not modify trading, broker, AI model, risk, or E*TRADE code.

Required post-install step:
The existing Python process on port 8767 must be fully stopped and restarted,
because Python keeps imported module code in memory.
