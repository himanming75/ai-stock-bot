# Release Notes

V121.01–V122.00 adds reconciliation between actual Alpaca Paper account state and internal autonomous runtime state.

Any blocking mismatch engages Safe Mode. The current actual account reports one open order while the internal runtime expects zero, so the demonstration correctly blocks autonomous ordering pending order-identity reconciliation.
