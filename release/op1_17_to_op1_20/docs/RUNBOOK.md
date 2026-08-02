# Windows Schedule Runbook

1. Confirm OP1.13-OP1.16 is genuinely ready.
2. Copy and review schedule and recovery inputs.
3. Run test and verify.
4. Review `windows_task_plan.json`.
5. Confirm Paper credentials exist as Windows user environment variables.
6. Run `INSTALL_OP1_READ_ONLY_WINDOWS_TASK.ps1` explicitly.
7. Verify the task in Task Scheduler.
8. Use the uninstall script for rollback.
