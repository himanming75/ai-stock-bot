
# Runbook

1. Install and run test-and-verify.
2. Run without flags to inspect the automatic schedule evaluation.
3. When `LOCAL_TRIGGER_READY`, run once with `-CreateTrigger`.
4. Review `automatic_schedule_trigger_plan.json`.
5. The next stage will dispatch the trigger to V83.17.
6. After successful dispatch, run with `-CompleteTrigger`.
7. Use `-ClearTriggerLock` only after investigating an interrupted trigger.
8. No Windows Task, continuous loop, or broker order is enabled.
