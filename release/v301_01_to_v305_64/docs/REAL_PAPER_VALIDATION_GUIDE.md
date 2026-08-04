# V301-V305 Real Paper Validation Activation

This stage performs read-only Alpaca Paper validation:

- credential presence
- paper endpoint enforcement
- account read
- market clock read
- positions read
- open orders read
- live endpoint protection

No order is submitted in this stage.

Environment variables:
- ALPACA_PAPER_API_KEY
- ALPACA_PAPER_SECRET_KEY

Enable read-only validation with ENABLE_V301_REAL_PAPER_READ.ps1.
