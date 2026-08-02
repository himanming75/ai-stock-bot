# V139.07 Test Results

Automated cases:

1. Wait before eligibility.
2. Valid inputs create preview and wait for approval.
3. Approval without enable remains disabled.
4. Approval plus enable creates only a local preparation token.
5. Eligibility token mismatch blocks.
6. Invalid quantity blocks.
7. Limit order without a positive limit price blocks.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V139_07_TEST_AND_VERIFY.ps1
```
