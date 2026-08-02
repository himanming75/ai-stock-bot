# V139.08 Test Results

Automated cases:

1. Wait before submission preparation.
2. ACCEPTED creates an acceptance token.
3. PENDING_NEW follows the accepted path.
4. REJECTED is recorded without lifecycle token.
5. Missing snapshot after preparation blocks.
6. Client order ID mismatch blocks.
7. Quantity mismatch blocks.
8. Unsupported initial status blocks.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V139_08_TEST_AND_VERIFY.ps1
```
