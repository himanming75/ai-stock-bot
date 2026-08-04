# V351.01–V360.64 Paper Order Proposal & Approval Gate

## Scope

- V351 Decision-to-order proposal conversion
- V352 Buying-power validation
- V353 Position-quantity validation
- V354 Market-hours validation
- V355 Duplicate-order detection
- V356 Daily-loss and notional limits
- V357 Kill-switch enforcement
- V358 Approval-token generation
- V359 Proposal ledger and replay integrity
- V360.64 Final safety audit

## Important

The output is a proposal only. Approval defaults to false and submission is always false.
No broker client is called.

## Run

```powershell
& .\RUN_V351_01_TO_V360_64_PAPER_ORDER_PROPOSAL.ps1
```

## Test and verify

```powershell
& .\RUN_V351_01_TO_V360_64_TEST_AND_VERIFY.ps1
```
