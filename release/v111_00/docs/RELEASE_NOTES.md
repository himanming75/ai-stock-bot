# Release Notes

V110.01–V111.00 adds controlled Alpaca Paper account read validation.

The Paper Trading API uses `paper-api.alpaca.markets`, and private requests use the paper key ID and secret headers. The standard pipeline remains fully offline. An additional explicit runner can issue only five read-only GET requests. Order submission and cancellation remain disabled.
