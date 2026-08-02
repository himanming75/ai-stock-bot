# DASH2.05 Actual Paper Snapshot Hotfix

This hotfix removes all Dashboard dependency on example Account, Position,
and Risk-derived position values.

The collector performs four read-only Paper API GET requests:

- `/v2/account`
- `/v2/positions`
- `/v2/orders?status=open`
- `/v2/clock`

The Dashboard displays account, position, open-order, and market-open values
only when the actual snapshot exists and is no more than five minutes old.
