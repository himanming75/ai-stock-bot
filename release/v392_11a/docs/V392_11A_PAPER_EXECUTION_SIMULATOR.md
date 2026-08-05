# V392.11A Paper Execution Simulator

## Purpose

Create a local simulated Fill Event from a V392.10A local paper order.

## Supported behavior

- reference price;
- configurable slippage in basis points;
- requested quantity calculation;
- full fill;
- partial fill;
- no fill;
- remaining quantity;
- simulated filled notional;
- replay protection;
- immutable Fill Event hash.

## Boundary

This simulator does not contact Alpaca or any broker. No external Paper or Live
order is submitted. The generated Fill Event is local-only and proceeds to the
next accounting stage.
