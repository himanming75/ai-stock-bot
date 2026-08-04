# AI Stock Bot V105 Final — Operator Guide

## Operating mode

- Paper trading only
- Manual approval required
- Live trading disabled
- Broker write disabled
- Order submission disabled
- External network disabled by the final release safety boundary

## Install

Run `INSTALL_AND_SAVE_V105_33_TO_V105_64_ONE_CLICK.ps1` from the extracted release package.

## Verify

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V105_33_TO_V105_64_TEST_AND_VERIFY.ps1
```

## Run final release verification

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V105_33_TO_V105_64.ps1
```

## Important

The final package certifies the completed paper-trading architecture. It does not activate live broker order submission.
