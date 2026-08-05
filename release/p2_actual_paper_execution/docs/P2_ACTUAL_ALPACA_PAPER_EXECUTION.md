# P2 Actual Alpaca Paper Execution

## Scope

P2 implements the canonical Alpaca Paper write boundary.

Included:

- Market and Limit orders;
- BUY and SELL;
- whole-share quantity;
- fractional/notional Market orders;
- Time in Force;
- Client Order ID;
- request hashing and idempotency;
- account, buying power, market clock, asset and symbol checks;
- Kill Switch;
- risk permission;
- per-order notional limit;
- daily order limit;
- explicit Paper network/write confirmation;
- submit, cancel and replace transports;
- request, response and error ledgers;
- Alpaca Request ID preservation.

## Default state

Installation and qualification submit zero orders. The P1 Kill Switch remains
active. Actual submission requires the operator to:

1. rotate any previously exposed API key;
2. provide Paper credentials locally;
3. enable Paper network access;
4. enable Paper write access;
5. set the exact confirmation phrase;
6. configure allowed symbols and limits;
7. explicitly deactivate the P1 Kill Switch;
8. run the actual submit command while the market is open.

## Boundary

Live API domain and Live submission are not supported by P2.
