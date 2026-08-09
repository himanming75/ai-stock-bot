# V2.1.21 Actual Intraday Canonical End-to-End Validation

Base commit: `a7895093`

Reuses the existing chain:
V2.1.14 session/freshness -> V2.1.15 one observation -> V2.1.16 evidence -> existing canonical real-market shadow -> V2.1.20 provenance -> V2.1.17 qualification.

Outside the regular weekday 09:30-16:00 ET clock window, the validator returns `WAITING_FOR_MARKET_SESSION` before creating the market-data runtime. The repository session classifier intentionally does not claim holiday verification.

This stage performs one bounded validation cycle only. It does not start E*TRADE OAuth, Preview, Place, or any broker order. PROD and live remain locked.

Possible actual statuses:
- WAITING_FOR_MARKET_SESSION
- BLOCKED_BY_SESSION_FRESHNESS
- PASS_FRESH_NO_ELIGIBLE_SIGNAL
- BLOCKED_BY_CANONICAL_PROVENANCE
- PASS_ACTUAL_INTRADAY_CANONICAL_NOT_READY
- PASS_ACTUAL_INTRADAY_CANONICAL_READY
