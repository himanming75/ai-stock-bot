
# Runbook

1. Install the bundle and run test-and-verify.
2. End or close the Paper Session after market close.
3. Ensure no scheduler tick or Intraday Loop remains active.
4. Run without flags to inspect end-of-day gates.
5. When the state is `END_OF_DAY_READY_TO_CERTIFY`, run with `-CertifyDay`.
6. After certification succeeds, run with `-PrepareNextDay`.
7. No Alpaca paper or live order is submitted.
