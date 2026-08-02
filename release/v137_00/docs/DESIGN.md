# V136.01–V137.00 Controlled Next-Order Execution Preview

This stage transforms a valid V136 cycle token into a complete local submission-preview package.

The package contains:

- order preview and broker request payload
- risk snapshot
- exposure snapshot
- final approval gate

Only market/day orders are permitted. Quantity and estimated-notional caps remain enforced.

The approval gate explicitly sets `actual_submission_allowed=false`. No broker network call or order submission occurs.
