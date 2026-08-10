# Backtest Route Repair

Reason:
The first Backtest Web installer expected a standalone POST route statement,
while the actual Web Controller uses one if/elif chain.

This repair:
- preserves the already-installed Backtest UI;
- preserves backtest_api.py;
- adds the /api/backtest GET route if missing;
- adds the /api/backtest/action POST route into the existing elif chain;
- is idempotent and safe to run again;
- compiles server.py and verifies both routes.

No broker writes, order submission, or Live trading capability are added.
