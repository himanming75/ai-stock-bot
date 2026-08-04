# AI Stock Bot V220 Final Production Operator Guide

## Release scope

V220 integrates and audits the completed Paper, Web, Qualification, Scheduler,
Portfolio, Multi-Broker, Broker Plugin, Risk Engine V2 and Strategy Ensemble layers.

## Safe operating mode

- Paper trading may be operated.
- Live account reads may remain read-only.
- Live broker write is disabled.
- Live submission is disabled.
- Automatic strategy promotion is disabled.
- Manual live activation remains a separate future qualification process.

## Daily startup

1. Activate `.venv`.
2. Run `RUN_V216_01_TO_V220_64.ps1`.
3. Confirm `actual_live_orders_submitted` is `0`.
4. Start the web controller.
5. Operate Paper mode and collect qualification history.

## Final release bundle

The generated bundle is stored under:

`release/v216_01_to_v220_64/bundle/AI_STOCK_BOT_V220_FINAL_PRODUCTION.zip`

The bundle must not be committed to Git. Keep it as an offline recovery artifact.

## Rollback

Stop the web controller and scheduled tasks before rollback.
Run the rollback script only from a clean Git working tree.
The rollback script requires the operator to type `ROLLBACK`.
