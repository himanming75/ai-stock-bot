# V361.01–V370.64 Controlled Paper Auto Execution

This stage contains the first real Alpaca Paper submission path.

Installation, tests, dry run, and verification submit zero orders. The default policy keeps Paper submission off.

A real Paper order requires all of the following:
- policy explicitly enabled;
- proposal approved and unexpired;
- exact enable phrase;
- `--allow-paper-network`;
- valid Paper credentials;
- Alpaca Paper endpoint only;
- market open and account active;
- SPY only;
- market/day only;
- maximum $1 notional;
- maximum one order per UTC day;
- no duplicate proposal or open order;
- kill switch off.

Live endpoint usage is rejected.
