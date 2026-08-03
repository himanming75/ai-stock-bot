
# Runbook

1. Install the bundle and run test-and-verify.
2. Normal execution reads the latest shadow signal and risk result.
3. BUY/SELL require an open market session, clear risk, valid symbol, and positive quantity.
4. HOLD becomes `NO_ACTION`.
5. Every decision is written to the authorization ledger.
6. No paper or live order is submitted.
