# V392.13A Paper Portfolio Reconciliation

## Purpose

Reconcile the local Paper Portfolio after V392.12A accounting.

## Checks

- Portfolio version;
- cash and equity;
- position quantity;
- average cost;
- market value;
- realized P&L;
- unrealized P&L;
- applied Fill Registry uniqueness;
- Accounting Event linkage;
- Portfolio, Registry, and Accounting Event hashes.

## Fail-closed behavior

Any mismatch blocks the next Autonomous Paper Cycle stage.

## Boundary

This stage performs local validation only. It does not contact a broker or
submit Paper/Live orders.
