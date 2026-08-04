# V381.01–V390.64 Portfolio Sync & Recovery

## Scope

- V381 account snapshot synchronization
- V382 position snapshot synchronization
- V383 cash drift detection
- V384 equity and portfolio-value drift detection
- V385 buying-power drift detection
- V386 missing/discovered position detection
- V387 position quantity drift detection
- V388 portfolio health classification
- V389 recovery-plan ledger
- V390.64 sync and recovery verification

## Safety

This stage is read-only.

Recovery plans are recommendations only. Automatic repair, broker writes,
order submission, cancellation, and position changes are disabled.

## Safe dry run

```powershell
& .\RUN_V381_01_TO_V390_64_SAFE_DRY_RUN.ps1
```

## Read Paper account

```powershell
& .\RUN_V381_01_TO_V390_64_READ_PAPER_PORTFOLIO.ps1
```
