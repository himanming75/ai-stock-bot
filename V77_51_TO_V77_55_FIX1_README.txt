V77.51-V77.55 FIX 1

Cause:
V77.51 copied the final V77.48 simulated trade quantity without constraining it
to V77.41 buying power or held-position quantity. V77.52 correctly rejected it.

Fix:
- Cap BUY quantity to current buying power.
- Cap SELL quantity to the currently held position.
- If the requested BUY is unaffordable but a position exists, create a valid
  paper-only SELL intent for that position.
- Add a regression test for the real portfolio-capacity mismatch.

Install:
Extract this ZIP over C:\stock-bot and replace the two files.
Then run:
powershell -ExecutionPolicy Bypass -File .\RUN_V77_51_TO_V77_55.ps1
