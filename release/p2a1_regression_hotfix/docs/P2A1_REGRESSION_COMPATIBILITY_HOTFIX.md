# P2A1 Regression Compatibility Hotfix

P2A changed `submit_paper_order()` from the unsafe `reference_price` parameter
to:

- `latest_trade_price`;
- `positions`.

The original P2 regression test and offline qualification script still called
the old signature. P2A1 updates those callers and verifies that
`reference_price` is no longer accepted.

This is a P2/P2A defect correction and does not add a roadmap stage.
