# V124.01–V125.00 Broker Portfolio Reconciliation

This release compares the Alpaca Paper broker state with the internal portfolio and recovered order ledger.

Compared fields:

- cash
- equity
- buying power
- position count
- held symbols
- position quantity
- average entry price
- market value
- unrealized P/L
- open-order count
- reserved BUY notional

Any mismatch engages Safe Mode and prevents autonomous ordering.

The standard demo uses the previously captured actual account read and recovered Legacy Bot order. The optional actual runner performs GET-only requests for account, positions, and open orders.
