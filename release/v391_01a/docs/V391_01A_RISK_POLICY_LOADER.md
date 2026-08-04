# V391.01A Risk Policy Loader

## Purpose

Create the validated policy foundation for the Autonomous Risk Governor.

## Enforced policy boundaries

- Paper endpoint only;
- Live submission disabled;
- broker writes disabled;
- daily-loss limit no greater than 5%;
- maximum drawdown no greater than 20%;
- single-position and symbol exposure no greater than 25%;
- maximum ten consecutive losses;
- kill switch required;
- manual resume required;
- automatic resume disabled.

## Behavior

The policy is loaded as UTF-8 or UTF-8 with BOM, validated, and hashed using
SHA-256 canonical JSON. Invalid policies produce `RISK_POLICY_BLOCKED`.

This stage does not read the broker and does not submit or modify orders.

## Next

V391.02A adds the Daily Loss Guard.
