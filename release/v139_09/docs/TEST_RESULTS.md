# V139.09 Test Results

Automated cases:

1. Wait before acceptance.
2. Accepted active-order monitoring.
3. Partial fill and remaining quantity.
4. Filled terminal state.
5. Canceled terminal state.
6. Filled quantity regression blocks.
7. Status regression blocks.
8. Filled quantity above order quantity blocks.
9. Missing lifecycle snapshot after acceptance blocks.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V139_09_TEST_AND_VERIFY.ps1
```
