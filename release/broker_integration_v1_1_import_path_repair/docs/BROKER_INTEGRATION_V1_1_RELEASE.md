# Broker Integration V1.1 Import Path Repair

## Root cause
The original Broker Integration V1 tests were executed by file path:

`python .\tests\test_broker_integration_v1.py`

In that mode Python used the `tests` directory as the first import path and did not reliably expose `C:\stock-bot` as the project import root.

The new bridge correctly reused `broker.contracts_v77_1`, but the test runner could not import the existing `broker` package.

## Repair
- Insert the repository root into `sys.path` in both Broker V1 test scripts.
- Set `PYTHONPATH=C:\stock-bot` in `RUN_BROKER_INTEGRATION_V1.ps1`.
- Preserve the existing partial Broker V1 implementation.
- Re-run the original V1 server/UI patches idempotently.
- Re-run all tests and the original V1 verify script.
- Commit/push only after PASS.

## Non-duplication
No new Broker Contract is created.
The existing `broker.contracts_v77_1` remains canonical.
No new Alpaca market-data stack is created.

## Safety
Network remains locked.
Broker write remains locked.
Order submission remains locked.
Live trading remains locked.
