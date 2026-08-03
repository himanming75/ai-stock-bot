
# Runbook

1. Install the bundle and run test-and-verify.
2. Add any required market holiday dates to the policy file.
3. Run without flags to evaluate the current session state.
4. Use `-StartSession` only during the configured regular market window.
5. Use `-EndSession` to write the daily snapshot and close the session.
6. Use `-RecoverSession` only when an active lock exists but session state is absent.
7. No paper or live order is submitted in this stage.
