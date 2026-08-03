# V97.33-V97.64 Paper Broker Read Model & Snapshot Reconciliation

## Included

- V97.33-V97.40 normalized broker account and position read models
- V97.41-V97.48 account snapshot reconciliation
- V97.49-V97.56 position quantity, average-cost and market-value reconciliation
- V97.57-V97.64 snapshot freshness, integrity certificate, audit ledger, tests and release

The stage remains read-only and paper-only. Credentials, external network, broker writes and order submissions remain disabled.

## Fixed reconciliation behavior

When an internal position has a missing or zero `market_value`, the read model now derives it as `quantity × mark_price`. The result records whether the value was reported or calculated.
