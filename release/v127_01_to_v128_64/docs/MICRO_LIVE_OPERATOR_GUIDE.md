# V127-V128 Micro-Live Readiness

This stage does not submit a live order.

It creates:

- micro-live candidates from Paper Shadow plans
- strict quantity and notional checks
- daily live-order and daily-loss checks
- two-step manual approval request
- approval-token model
- replay and expiry placeholders
- Paper-versus-Live Shadow comparison
- hard-blocked Live gateway

Current defaults:

- maximum quantity: 1 share
- maximum order notional: $250
- maximum daily live orders: 1
- maximum daily live loss: $20
- live network: disabled
- live submission: disabled
- actual live orders: 0

Do not enable Live networking or submission until a later controlled stage is reviewed separately.
